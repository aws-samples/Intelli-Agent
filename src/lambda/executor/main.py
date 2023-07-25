import json
import logging
import os
import boto3
import time
import uuid
import langchain
from aos_utils import OpenSearchClient
from llmbot_utils import QueryType, combine_recalls, concat_recall_knowledge
from ddb_utils import get_session, update_session
from sm_utils import get_vector_by_sm_endpoint, get_cross_by_sm_endpoint, generate_answer

A_Role="用户"
B_Role="AWSBot"
STOP=[f"\n{A_Role}", f"\n{B_Role}"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sm_client = boto3.client("sagemaker-runtime")
chat_session_table = os.environ.get('chat_session_table')

class APIException(Exception):
    def __init__(self, message, code: str = None):
        if code:
            super().__init__("[{}] {}".format(code, message))
        else:
            super().__init__(message)

def handle_error(func):
    """Decorator for exception handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIException as e:
            logger.exception(e)
            raise e
        except Exception as e:
            logger.exception(e)
            raise RuntimeError(
                "Unknown exception, please check Lambda log for more details"
            )

    return wrapper

def main_entry(session_id:str, query_input:str, history:list, embedding_model_endpoint:str, cross_model_endpoint:str, 
               llm_model_endpoint:str, aos_endpoint:str, aos_index:str, aos_result_num:int, 
               enable_knowledge_qa:bool, temperature: float):
    """
    Entry point for the Lambda function.

    :param session_id: The ID of the session.
    :param query_input: The query input.
    :param embedding_model_endpoint: The endpoint of the embedding model.
    :param cross_model_endpoint: The endpoint of the cross model.
    :param llm_model_endpoint: The endpoint of the language model.
    :param llm_model_name: The name of the language model.
    :param aos_endpoint: The endpoint of the AOS engine.
    :param aos_index: The index of the AOS engine.
    :param aos_knn_field: The knn field of the AOS engine.
    :param aos_result_num: The number of results of the AOS engine.
    :param enable_knowledge_qa: Whether to enable knowledge QA.
    :param temperature: The temperature of the language model.

    return: answer(str)
    """
    sm_client = boto3.client("sagemaker-runtime")
    aos_client = OpenSearchClient(aos_endpoint)
    
    # 1. get_session
    start1 = time.time()
    elpase_time = time.time() - start1
    logger.info(f'runing time of get_session : {elpase_time}s seconds')

    if enable_knowledge_qa:
        #query_knowledge = query_input
        query_knowledge = ''.join([query_input] + [row[0] for row in history][::-1])
        
        # 2. get AOS knn recall 
        start = time.time()
        
        query_embedding = get_vector_by_sm_endpoint(query_knowledge, sm_client, embedding_model_endpoint)
        opensearch_knn_respose = aos_client.search(index_name=aos_index, query_type="knn", query_term=query_embedding[0])
        elpase_time = time.time() - start
        logger.info(f'runing time of opensearch_knn : {elpase_time}s seconds')
        
        # 3. get AOS invertedIndex recall
        start = time.time()
        opensearch_query_response = aos_client.search(index_name=aos_index, query_type="basic", query_term=query_knowledge)
        elpase_time = time.time() - start
        logger.info(f'runing time of opensearch_query : {elpase_time}s seconds')

        # 4. combine these two opensearch_knn_respose and opensearch_query_response
        recall_knowledge = combine_recalls(opensearch_knn_respose, opensearch_query_response)
        
        # 5. Predict correlation score
        recall_knowledge_cross = []
        for knowledge in recall_knowledge:
            score = get_cross_by_sm_endpoint(query_knowledge, knowledge['doc'], sm_client, cross_model_endpoint)
            logger.info(json.dumps({"doc": knowledge['doc'], "score": score}, ensure_ascii=False))
            if score > 0.8:
                recall_knowledge_cross.append({'doc': knowledge['doc'], 'score': score})

        recall_knowledge_cross.sort(key=lambda x: x["score"], reverse=True)

        recall_knowledge_str = concat_recall_knowledge(recall_knowledge_cross[:2])
        query_type = QueryType.KnowledgeQuery
        elpase_time = time.time() - start
        logger.info(f'runing time of recall knowledge : {elpase_time}s seconds')
    else:
        recall_knowledge_str = ""
        opensearch_query_response, opensearch_knn_respose, recall_knowledge = [], [], []
        query_type = QueryType.Conversation

    # 6. generate answer using question and recall_knowledge
    parameters = {'temperature': temperature}
    try:
        answer = generate_answer(sm_client, llm_model_endpoint, question=query_input, context = recall_knowledge_str, history=history, stop=STOP, parameters=parameters)
    except Exception as e:
        logger.info(f'Exceptions: str({e})')
        answer = ""
    
    # 7. update_session
    start = time.time()
    update_session(session_id=session_id, chat_session_table=chat_session_table, 
                   question=query_input, answer=answer, intention=str(query_type))
    elpase_time = time.time() - start
    elpase_time1 = time.time() - start1
    logger.info(f'runing time of update_session : {elpase_time}s seconds')
    logger.info(f'runing time of all  : {elpase_time1}s seconds')

    # 8. log results
    json_obj = {
        "query": query_input,
        "recall_knowledge" : recall_knowledge,
        "recall_knowledge_cross_str": recall_knowledge_str,
        "STOP": STOP,
        "detect_query_type": str(query_type)
    }

    json_obj['session_id'] = session_id
    json_obj['chatbot_answer'] = answer
    json_obj['timestamp'] = int(time.time())
    json_obj['log_type'] = "all"
    json_obj_str = json.dumps(json_obj, ensure_ascii=False)
    logger.info(json_obj_str)

    return answer

@handle_error
def lambda_handler(event, context):

    logger.info(f"event:{event}")

    model = event['model']
    
    messages = event['messages']
    human = []
    assistant = []
    history = []
    for line in messages:
        if line['role'] in ("system", "user"):
            if len(assistant):
                history.append('\n'.join(assistant))
                assistant = []
            human.append(line['content'])
        else:
            if len(human):
                history.append('\n'.join(human))
                human = []
            assistant.append(line['content'])
    history = [[history[i], history[i+1]] for i in range(0, len(history), 2)]
    question = human[0]
    
    role = "user"
    
    temperature = event['temperature']
    request_timestamp = time.time() # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    session_id = f"{role}_{int(request_timestamp)}"

    # knowledge_qa_flag is True if model == 'knowledge_qa' else False
    knowledge_qa_flag = True if model == 'knowledge_qa' else False

    logger.info(f'request_timestamp :{request_timestamp}')
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")

    # 接收触发AWS Lambda函数的事件
    logger.info('The main brain has been activated, aws🚀!')

    # 1. 获取环境变量
    embedding_endpoint = os.environ.get("embedding_endpoint", "")
    cross_endpoint = os.environ.get("cross_endpoint", "")
    aos_endpoint = os.environ.get("aos_endpoint", "")
    aos_index = os.environ.get("aos_index", "")
    aos_knn_field = os.environ.get("aos_knn_field", "")
    aos_result_num = int(os.environ.get("aos_results", ""))

    llm_endpoint = os.environ.get('llm_default_endpoint')

    logger.info(f'llm_endpoint : {llm_endpoint}')
    logger.info(f'embedding_endpoint : {embedding_endpoint}')
    logger.info(f'cross_endpoint : {cross_endpoint}')
    logger.info(f'aos_endpoint : {aos_endpoint}')
    logger.info(f'aos_index : {aos_index}')
    logger.info(f'aos_knn_field : {aos_knn_field}')
    logger.info(f'aos_result_num : {aos_result_num}')
    
    main_entry_start = time.time()  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    answer = main_entry(session_id, question, history, embedding_endpoint, cross_endpoint, llm_endpoint, aos_endpoint, aos_index, aos_result_num, knowledge_qa_flag, temperature)
    main_entry_elpase = time.time() - main_entry_start  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    logger.info(f'runing time of main_entry : {main_entry_elpase}s seconds')


    # 2. return rusult

    return {
        "id": session_id,
        "object": "chat.completion",
        "created": int(request_timestamp),
        "model": model,
        "usage": {
            "prompt_tokens": 13,
            "completion_tokens": 7,
            "total_tokens": 20
        },
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": answer
                },
                "finish_reason": "stop",
                "index": 0
            }
        ]
    }
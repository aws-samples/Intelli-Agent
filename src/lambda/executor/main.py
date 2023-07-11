import json
import logging
import os
import boto3
import time
import uuid
from enum import Enum
import langchain
from aos_search import search_using_aos_knn, aos_search
from llmbot_utils import combine_recalls, qa_knowledge_prompt_build, conversion_prompt_build
from ddb_utils import get_session, update_session
from sagemaker_utils import get_vector_by_sm_endpoint, generate_answer

A_Role="用户"
B_Role="AWSBot"
STOP=[f"\n{A_Role}", f"\n{B_Role}"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sm_client = boto3.client("sagemaker-runtime")
chat_session_table = os.environ.get('chat_session_table')

class QueryType(Enum):
    KeywordQuery   = "KeywordQuery"       #用户仅仅输入了一些关键词（2 token)
    KnowledgeQuery = "KnowledgeQuery"     #用户输入的需要参考知识库有关来回答
    Conversation   = "Conversation"       #用户输入的是跟知识库无关的问题

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

def main_entry(session_id:str, query_input:str, embedding_model_endpoint:str, llm_model_endpoint:str, llm_model_name:str, aos_endpoint:str, aos_index:str, aos_knn_field:str, aos_result_num:int):
    """
    Entry point for the Lambda function.

    Parameters:
        session_id (str): The ID of the session.
        query_input (str): The query input.
        embedding_model_endpoint (str): The endpoint of the embedding model.
        llm_model_endpoint (str): The endpoint of the language model.
        aos_endpoint (str): The endpoint of the AOS engine.
        aos_index (str): The index of the AOS engine.
        aos_knn_field (str): The knn field of the AOS engine.
        aos_result_num (int): The number of results of the AOS engine.

    return: answer(str)
    """
    sm_client = boto3.client("sagemaker-runtime")
    
    # 1. get_session
    import time
    start1 = time.time()
    session_history = get_session(session_id=session_id, chat_session_table=chat_session_table)
    elpase_time = time.time() - start1
    logger.info(f'runing time of get_session : {elpase_time}s seconds')

    # 3. get AOS knn recall 
    start = time.time()
    query_embedding = get_vector_by_sm_endpoint(query_input, sm_client, embedding_model_endpoint)
    opensearch_knn_respose = search_using_aos_knn(query_embedding[0], aos_endpoint, aos_index)
    elpase_time = time.time() - start
    logger.info(f'runing time of opensearch_knn : {elpase_time}s seconds')
    
    # 4. get AOS invertedIndex recall
    start = time.time()
    opensearch_query_response = aos_search(aos_endpoint, aos_index, "doc", query_input)
    elpase_time = time.time() - start
    logger.info(f'runing time of opensearch_query : {elpase_time}s seconds')

    # 5. combine these two opensearch_knn_respose and opensearch_query_response
    recall_knowledge = combine_recalls(opensearch_knn_respose, opensearch_query_response)
    recall_knowledge.sort(key=lambda x: x["score"])
    recall_knowledge = recall_knowledge[-2:]

    # 6. check is it keyword search
    exactly_match_result = aos_search(aos_endpoint, aos_index, "doc", query_input, exactly_match=True)

    answer = None
    final_prompt = None
    query_type = None
    free_chat_coversions = []
    if exactly_match_result and recall_knowledge: 
        query_type = QueryType.KeywordQuery
        answer = exactly_match_result[0]["doc"]
        final_prompt = ""
    elif recall_knowledge:
        query_type = QueryType.KnowledgeQuery
        final_prompt = qa_knowledge_prompt_build(query_input, recall_knowledge, role_a=A_Role, role_b=B_Role)
    else:
        query_type = QueryType.Conversation
        free_chat_coversions = [ item for item in session_history if item[2] == QueryType.Conversation ]
        final_prompt = conversion_prompt_build(query_input, free_chat_coversions[-2:], role_a=A_Role, role_b=B_Role)

    json_obj = {
        "query": query_input,
        "opensearch_doc":  opensearch_query_response,
        "opensearch_knn_doc":  opensearch_knn_respose,
        "kendra_doc": [],
        "knowledges" : recall_knowledge,
        "detect_query_type": str(query_type),
        "LLM_input": final_prompt
    }

    try:
        if final_prompt:
            answer = generate_answer(sm_client, llm_model_endpoint, question=query_input, context= recall_knowledge, stop=STOP)
            
        json_obj['session_id'] = session_id
        json_obj['chatbot_answer'] = answer
        json_obj['conversations'] = free_chat_coversions
        json_obj['timestamp'] = int(time.time())
        json_obj['log_type'] = "all"
        json_obj_str = json.dumps(json_obj, ensure_ascii=False)
    except Exception as e:
        logger.info(f'Exceptions: str({e})')
    finally:
        json_obj_str = json.dumps(json_obj, ensure_ascii=False)
        logger.info(json_obj_str)

    start = time.time()
    update_session(session_id=session_id, chat_session_table=chat_session_table, 
                   question=query_input, answer=answer, intention=str(query_type))
    elpase_time = time.time() - start
    elpase_time1 = time.time() - start1
    logger.info(f'runing time of update_session : {elpase_time}s seconds')
    logger.info(f'runing time of all  : {elpase_time1}s seconds')

    return answer


@handle_error
def lambda_handler(event, context):

    logger.info(f"event:{event}")
    session_id = event['chat_name']
    question = event['prompt']
    model_name = event['model']

    # model_name = 'chatglm-7b'
    llm_endpoint = None
    if model_name in ['chatglm', 'bloomz', 'llama', 'alpaca']:
        llm_endpoint = os.environ.get('llm_{}_endpoint'.format(model_name))
    else:
        llm_endpoint = os.environ.get('llm_default_endpoint')

    # 获取当前时间戳
    request_timestamp = time.time()  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    logger.info(f'request_timestamp :{request_timestamp}')
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")

    # 接收触发AWS Lambda函数的事件
    logger.info('The main brain has been activated, aws🚀!')

    # 1. 获取环境变量
    embedding_endpoint = os.environ.get("embedding_endpoint", "")
    aos_endpoint = os.environ.get("aos_endpoint", "")
    aos_index = os.environ.get("aos_index", "")
    aos_knn_field = os.environ.get("aos_knn_field", "")
    aos_result_num = int(os.environ.get("aos_results", ""))

    logger.info(f'model_name : {model_name}')
    logger.info(f'llm_endpoint : {llm_endpoint}')
    logger.info(f'embedding_endpoint : {embedding_endpoint}')
    logger.info(f'aos_endpoint : {aos_endpoint}')
    logger.info(f'aos_index : {aos_index}')
    logger.info(f'aos_knn_field : {aos_knn_field}')
    logger.info(f'aos_result_num : {aos_result_num}')
    
    main_entry_start = time.time()  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    answer = main_entry(session_id, question, embedding_endpoint, llm_endpoint, model_name, aos_endpoint, aos_index, aos_knn_field, aos_result_num)
    main_entry_elpase = time.time() - main_entry_start  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    logger.info(f'runing time of main_entry : {main_entry_elpase}s seconds')


    # 2. return rusult

    # Sample Response:
    # "id": "设置一个uuid"
    # "created": "1681891998"
    # "model": "模型名称"
    # "choices": [{"text": "模型回答的内容"}]
    # "usage": {"prompt_tokens": 58, "completion_tokens": 15, "total_tokens": 73}}]

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': [{
            "id": str(uuid.uuid4()),
            "created": request_timestamp,
            "useTime": time.time() - request_timestamp,
            "model": "main_brain",
            "choices":[{"text": answer}],
            "usage": {"prompt_tokens": 58, "completion_tokens": 15, "total_tokens": 73}
        }]
    }


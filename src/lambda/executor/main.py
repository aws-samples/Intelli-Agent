import json
import logging
import os
import boto3
import time
from aos_utils import LLMBotOpenSearchClient
from llmbot_utils import QueryType, combine_recalls, concat_recall_knowledge, process_input_messages
from ddb_utils import get_session, update_session
from sm_utils import SagemakerEndpointVectorOrCross

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region = os.environ['AWS_REGION']
embedding_endpoint = os.environ.get("embedding_endpoint", "")
cross_endpoint = os.environ.get("cross_endpoint", "")
aos_endpoint = os.environ.get("aos_endpoint", "")
aos_index = os.environ.get("aos_index", "")
llm_endpoint = os.environ.get('llm_default_endpoint', "")
chat_session_table = os.environ.get('chat_session_table', "")

sm_client = boto3.client("sagemaker-runtime")
aos_client = LLMBotOpenSearchClient(aos_endpoint)

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
               llm_model_endpoint:str, aos_index:str, enable_knowledge_qa:bool, temperature: float):
    """
    Entry point for the Lambda function.

    :param session_id: The ID of the session.
    :param query_input: The query input.
    :param history: The history of the conversation.
    :param embedding_model_endpoint: The endpoint of the embedding model.
    :param cross_model_endpoint: The endpoint of the cross model.
    :param llm_model_endpoint: The endpoint of the language model.
    :param llm_model_name: The name of the language model.
    :param aos_index: The index of the AOS engine.
    :param enable_knowledge_qa: Whether to enable knowledge QA.
    :param temperature: The temperature of the language model.

    return: answer(str)
    """

    if enable_knowledge_qa:
        # 1. concatenate query_input and history to unified prompt
        query_knowledge = ''.join([query_input] + [row[0] for row in history][::-1])
        
        # 2. get AOS knn recall 
        start = time.time()
        query_embedding = SagemakerEndpointVectorOrCross(prompt="为这个句子生成表示以用于检索相关文章：" + query_knowledge, endpoint_name=embedding_model_endpoint, region_name=region, model_type="vector", stop=None)
        opensearch_knn_respose = aos_client.search(index_name=aos_index, query_type="knn", query_term=query_embedding)
        logger.info(json.dumps(opensearch_knn_respose, ensure_ascii=False))
        elpase_time = time.time() - start
        logger.info(f'runing time of opensearch_knn : {elpase_time}s seconds')
        
        # 3. get AOS invertedIndex recall
        start = time.time()
        opensearch_query_response = aos_client.search(index_name=aos_index, query_type="basic", query_term=query_knowledge)
        logger.info(json.dumps(opensearch_query_response, ensure_ascii=False))
        elpase_time = time.time() - start
        logger.info(f'runing time of opensearch_query : {elpase_time}s seconds')

        # 4. combine these two opensearch_knn_respose and opensearch_query_response
        recall_knowledge = combine_recalls(opensearch_knn_respose, opensearch_query_response)
        
        # 5. Predict correlation score using cross model
        recall_knowledge_cross = []
        for knowledge in recall_knowledge:
            # get score using cross model
            score = float(SagemakerEndpointVectorOrCross(prompt=query_knowledge, endpoint_name=cross_model_endpoint, region_name=region, model_type="cross", stop=None, context=knowledge['doc']))
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
        query_type = QueryType.Conversation

    # 6. generate answer using question and recall_knowledge
    parameters = {'temperature': temperature}
    try:
        # generate_answer
        answer = SagemakerEndpointVectorOrCross(prompt=query_input, endpoint_name=llm_model_endpoint, region_name=region, model_type="answer", stop=None, history=history, parameters=parameters, context=recall_knowledge_str)
    except Exception as e:
        logger.info(f'Exceptions: str({e})')
        answer = ""
    
    # 7. update_session
    start = time.time()
    update_session(session_id=session_id, chat_session_table=chat_session_table, 
                   question=query_input, answer=answer, intention=str(query_type))
    elpase_time = time.time() - start
    logger.info(f'runing time of update_session : {elpase_time}s seconds')

    # 8. log results
    json_obj = {
        "session_id": session_id,
        "query": query_input,
        "recall_knowledge_cross_str": recall_knowledge_str,
        "detect_query_type": str(query_type),
        "history": history,
        "chatbot_answer": answer,
        "timestamp": int(time.time())
    }

    json_obj_str = json.dumps(json_obj, ensure_ascii=False)
    logger.info(json_obj_str)

    return answer

@handle_error
def lambda_handler(event, context):
    request_timestamp = time.time()
    logger.info(f'request_timestamp :{request_timestamp}')
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")

    # Get request body
    event_body = json.loads(event['body'])
    model = event_body['model']
    messages = event_body['messages']
    temperature = event_body['temperature']

    history, question = process_input_messages(messages)
    role = "user"
    session_id = f"{role}_{int(request_timestamp)}"
    knowledge_qa_flag = True if model == 'knowledge_qa' else False
    
    main_entry_start = time.time() 
    answer = main_entry(session_id, question, history, embedding_endpoint, cross_endpoint, llm_endpoint, aos_index, knowledge_qa_flag, temperature)
    main_entry_elpase = time.time() - main_entry_start  
    logger.info(f'runing time of main_entry : {main_entry_elpase}s seconds')

    llmbot_response = {
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

    # 2. return rusult
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(llmbot_response)
    }

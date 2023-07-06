import json
import logging
import os
import re
from botocore import config
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import boto3
import time
import requests
import uuid
# from transformers import AutoTokenizer
from enum import Enum
from typing import List
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import langchain
credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)


logger = logging.getLogger()
logger.setLevel(logging.INFO)
sm_client = boto3.client("sagemaker-runtime")
# llm_endpoint = 'bloomz-7b1-mt-2023-04-19-09-41-24-189-endpoint'
chat_session_table = os.environ.get('chat_session_table')
QA_SEP = "=>"
AWS_Free_Chat_Prompt = """你是云服务AWS的智能客服机器人{B}，能够回答{A}的各种问题以及陪{A}聊天，如:{chat_history}\n\n{A}: {question}\n{B}: """
AWS_Knowledge_QA_Prompt = """你是云服务AWS的智能客服机器人{B}，请严格根据反括号中的资料提取相关信息\n```\n{fewshot}\n```\n回答{A}的各种问题，比如:\n\n{A}: {question}\n{B}: """
A_Role="用户"
B_Role="AWSBot"
Fewshot_prefix_Q="问题"
Fewshot_prefix_A="回答"
STOP=[f"\n{A_Role}", f"\n{B_Role}"]

class ErrorCode:
    DUPLICATED_INDEX_PREFIX = "DuplicatedIndexPrefix"
    DUPLICATED_WITH_INACTIVE_INDEX_PREFIX = "DuplicatedWithInactiveIndexPrefix"
    OVERLAP_INDEX_PREFIX = "OverlapIndexPrefix"
    OVERLAP_WITH_INACTIVE_INDEX_PREFIX = "OverlapWithInactiveIndexPrefix"
    INVALID_INDEX_MAPPING = "InvalidIndexMapping"


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

# kendra


def query_kendra(Kendra_index_id="", lang="zh", search_query_text="what is s3?", Kendra_result_num=3):
    # 连接到Kendra
    client = boto3.client('kendra')

    # 构造Kendra查询请求
    query_result = client.query(
        IndexId=Kendra_index_id,
        QueryText=search_query_text,
        AttributeFilter={
            "EqualsTo": {
                "Key": "_language_code",
                "Value": {
                    "StringValue": lang
                }
            }
        }
    )
    # print(query_result['ResponseMetadata']['HTTPHeaders'])
    # kendra_took = query_result['ResponseMetadata']['HTTPHeaders']['x-amz-time-millis']
    # 创建一个结果列表
    results = []

    # 将每个结果添加到结果列表中
    for result in query_result['ResultItems']:
        # 创建一个字典来保存每个结果
        result_dict = {}

        result_dict['score'] = 0.0
        result_dict['doc_type'] = "P"

        # 如果有可用的总结
        if 'DocumentExcerpt' in result:
            result_dict['doc'] = result['DocumentExcerpt']['Text']
        else:
            result_dict['doc'] = ''

        # 将结果添加到列表中
        results.append(result_dict)

    # 输出结果列表
    return results[:Kendra_result_num]


# AOS
def get_vector_by_sm_endpoint(questions, sm_client, endpoint_name):
    parameters = {
        # "early_stopping": True,
        # "length_penalty": 2.0,
        "max_new_tokens": 50,
        "temperature": 0,
        "min_length": 10,
        "no_repeat_ngram_size": 2,
    }

    response_model = sm_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": questions,
                "parameters": parameters
            }
        ),
        ContentType="application/json",
    )
    json_str = response_model['Body'].read().decode('utf8')
    json_obj = json.loads(json_str)
    embeddings = json_obj['sentence_embeddings']
    return embeddings

def search_using_aos_knn(q_embedding, hostname, index, size=10):
    # awsauth = (username, passwd)
    # print(type(q_embedding))
    # logger.info(f"q_embedding:")
    # logger.info(q_embedding)
    headers = {"Content-Type": "application/json"}
    # query = {
    #     "size": size,
    #     "query": {
    #         "bool": {
    #             "must":[ {"term": { "doc_type": "P" }} ],
    #             "should": [ { "knn": { "embedding": { "vector": q_embedding, "k": size }}} ]
    #         }
    #     },
    #     "sort": [
    #         {
    #             "_score": {
    #                 "order": "asc"
    #             }
    #         }
    #     ]
    # }

    # reference: https://opensearch.org/docs/latest/search-plugins/knn/filter-search-knn/#boolean-filter-with-ann-search
    # query =  {
    #     "bool": {
    #         "filter": {
    #             "bool": {
    #                 "must": [{ "term": {"doc_type": "P" }}]
    #             }
    #         },
    #         "must": [
    #             {
    #                 "knn": {"embedding": { "vector": q_embedding, "k": size }}
    #             } 
    #         ]
    #     }
    # }


    #Note: 查询时无需指定排序方式，最临近的向量分数越高，做过归一化(0.0~1.0)
    query = {
        "size": size,
        "query": {
            "knn": {
                "embedding": {
                    "vector": q_embedding,
                    "k": size
                }
            }
        }
    }
    opensearch_knn_respose = []
    try:
        r = requests.post("https://"+hostname + "/" + index +
                        '/_search', headers=headers, json=query)
        results = json.loads(r.text)["hits"]["hits"]
        for item in results:
            opensearch_knn_respose.append( {'doc':"{}{}{}".format(item['_source']['doc'], QA_SEP, item['_source']['answer']),"doc_type":item["_source"]["doc_type"],"score":item["_score"]} )
        return opensearch_knn_respose
    except Exception as e:
        print(f'knn query exception:{str(e)}')
        return []
    


def aos_search(host, index_name, field, query_term, exactly_match=False, size=10):
    """
    search opensearch with query.
    :param host: AOS endpoint
    :param index_name: Target Index Name
    :param field: search field
    :param query_term: query term
    :return: aos response json
    """
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    query = None
    if exactly_match:
        query =  {
            "query" : {
                "match_phrase":{
                    "doc": query_term
                }
            }
        }
    else:
        query = {
            "size": size,
            "query": {
                "bool":{
                    "must":[ {"term": { "doc_type": "Q" }} ],
                    "should": [ {"match": { field : query_term }} ]
                }
            },
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                }
            ]
        }
    query_response = client.search(
        body=query,
        index=index_name
    )

    if exactly_match:
        result_arr = [ {'doc': item['_source']['answer'], 'doc_type': 'A', 'score': item['_score']} for item in query_response["hits"]["hits"]]
    else:
        result_arr = [ {'doc':"{}{}{}".format(item['_source']['doc'], QA_SEP, item['_source']['answer']), 'doc_type': item['_source']['doc_type'], 'score': item['_score']} for item in query_response["hits"]["hits"]]

    return result_arr

def get_session(session_id):

    table_name = chat_session_table
    dynamodb = boto3.resource('dynamodb')

    # table name
    table = dynamodb.Table(table_name)
    operation_result = ""

    response = table.get_item(Key={'session-id': session_id})

    if "Item" in response.keys():
        # print("****** " + response["Item"]["content"])
        operation_result = json.loads(response["Item"]["content"])
    else:
        # print("****** No result")
        operation_result = ""

    return operation_result


# param:    session_id
#           question
#           answer
# return:   success
#           failed
def update_session(session_id, question, answer, intention):

    table_name = chat_session_table
    dynamodb = boto3.resource('dynamodb')

    # table name
    table = dynamodb.Table(table_name)
    operation_result = ""

    response = table.get_item(Key={'session-id': session_id})

    if "Item" in response.keys():
        # print("****** " + response["Item"]["content"])
        chat_history = json.loads(response["Item"]["content"])
    else:
        # print("****** No result")
        chat_history = []

    chat_history.append([question, answer, intention])
    content = json.dumps(chat_history)

    # inserting values into table
    response = table.put_item(
        Item={
            'session-id': session_id,
            'content': content
        }
    )

    if "ResponseMetadata" in response.keys():
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            operation_result = "success"
        else:
            operation_result = "failed"
    else:
        operation_result = "failed"

    return operation_result

def enforce_stop_tokens(text: str, stop: List[str]) -> str:
    """Cut off the text as soon as any stop words occur."""
    if stop is None:
        return text
    
    return re.split("|".join(stop), text)[0]

def Generate(smr_client, llm_endpoint, prompt, llm_name, stop=None, history=[]):
    answer = None
    if llm_name == "chatglm":
        logger.info("call chatglm...")
        parameters = {
        "max_length": 2048,
        "temperature": 0.01,
        "num_beams": 1, # >1可能会报错，"probability tensor contains either `inf`, `nan` or element < 0"； 即使remove_invalid_values=True也不能解决
        "do_sample": False,
        "top_p": 0.7,
        "logits_processor" : None,
        # "remove_invalid_values" : True
        }
        response_model = smr_client.invoke_endpoint(
            EndpointName=llm_endpoint,
            Body=json.dumps(
            {
                "inputs": prompt,
                "parameters": parameters,
                "history" : history
            }
            ),
            ContentType="application/json",
        )

        json_ret = json.loads(response_model['Body'].read().decode('utf8'))

        answer = json_ret['outputs']
    elif llm_name == "bloomz":
        logger.info("call bloomz...")
        parameters = {
            # "early_stopping": True,
            "length_penalty": 1.0,
            "max_new_tokens": 200,
            "temperature": 0,
            "min_length": 20,
            "no_repeat_ngram_size": 200,
            # "eos_token_id": ['\n']
        }

        response_model = smr_client.invoke_endpoint(
            EndpointName=llm_endpoint,
            Body=json.dumps(
                {
                    "inputs": prompt,
                    "parameters": parameters
                }
            ),
            ContentType="application/json",
        )
        
        json_ret = json.loads(response_model['Body'].read().decode('utf8'))
        answer = json_ret['outputs'][len(prompt):]

    return enforce_stop_tokens(answer, stop)


class QueryType(Enum):
    KeywordQuery   = "KeywordQuery"       #用户仅仅输入了一些关键词（2 token)
    KnowledgeQuery = "KnowledgeQuery"     #用户输入的需要参考知识库有关来回答
    Conversation   = "Conversation"       #用户输入的是跟知识库无关的问题


# def intention_classify(post_text, prompt_template, few_shot_example):
#     prompt = prompt_template.format(
#         fewshot=few_shot_example, question=post_text)
#     result = Generate(sm_client, llm_endpoint, prompt)
#     return result

def conversion_prompt_build(post_text, conversations, role_a, role_b):
    chat_history = [ """{}: {}\n{}: {}""".format(role_a, item[0], role_b, item[1]) for item in conversations ]
    chat_histories = "\n\n".join(chat_history)
    chat_histories = f'\n\n{chat_histories}' if len(chat_histories) else ""

    # \n\n{fewshot}
    
    return AWS_Free_Chat_Prompt.format(chat_history=chat_histories, question=post_text, A=role_a, B=role_b)

# different scan
def qa_knowledge_prompt_build(post_text, qa_recalls, role_a, role_b):
    """
    Detect User intentions, build prompt for LLM. For Knowledge QA, it will merge all retrieved related document paragraphs into a single prompt
    Parameters examples:
        post_text : "介绍下强化部件"
        qa_recalls: [ {"doc" : doc1, "score" : score}, ]
    return: prompt string
    """
    qa_pairs = [ obj["doc"].split(QA_SEP) for obj in qa_recalls ]
    qa_fewshots = [ "{}: {}\n{}: {}".format(Fewshot_prefix_Q, pair[0], Fewshot_prefix_A, pair[1]) for pair in qa_pairs ]
    fewshots_str = "\n\n".join(qa_fewshots[-3:])
    return AWS_Knowledge_QA_Prompt.format(fewshot=fewshots_str, question=post_text, A=role_a, B=role_b)

def main_entry(session_id:str, query_input:str, embedding_model_endpoint:str, llm_model_endpoint:str, llm_model_name:str, aos_endpoint:str, aos_index:str, aos_knn_field:str, aos_result_num:int, kendra_index_id:str, kendra_result_num:int):
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
        kendra_index_id (str): The ID of the Kendra index.
        kendra_result_num (int): The number of results of the Kendra Service.

    return: answer(str)
    """
    sm_client = boto3.client("sagemaker-runtime")
    
    # 1. get_session
    import time
    start1 = time.time()
    session_history = get_session(session_id=session_id)
    elpase_time = time.time() - start1
    logger.info(f'runing time of get_session : {elpase_time}s seconds')

    # 2. get kendra recall 
    # start = time.time()
    # kendra_respose = [] # query_kendra(kendra_index_id, "zh", query_input, kendra_result_num)
    # elpase_time = time.time() - start
    # logger.info(f'runing time of query_kendra : {elpase_time}s seconds')

    # 3. get AOS knn recall 
    start = time.time()
    query_embedding = get_vector_by_sm_endpoint(query_input, sm_client, embedding_model_endpoint)
    opensearch_knn_respose = search_using_aos_knn(query_embedding[0], aos_endpoint, aos_index)
    elpase_time = time.time() - start
    logger.info(f'runing time of opensearch_knn : {elpase_time}s seconds')
    
    # 4. get AOS invertedIndex recall
    start = time.time()
    opensearch_query_response = aos_search(aos_endpoint, aos_index, "doc", query_input)
    # logger.info(opensearch_query_response)
    elpase_time = time.time() - start
    logger.info(f'runing time of opensearch_query : {elpase_time}s seconds')

    # 5. combine these two opensearch_knn_respose and opensearch_query_response
    def combine_recalls(opensearch_knn_respose, opensearch_query_response):
        '''
        filter knn_result if the result don't appear in filter_inverted_result
        '''
        knn_threshold = 0.2
        inverted_theshold = 5.0
        filter_knn_result = { item["doc"] : item["score"] for item in opensearch_knn_respose if item["score"]> knn_threshold }
        filter_inverted_result = { item["doc"] : item["score"] for item in opensearch_query_response if item["score"]> inverted_theshold }

        combine_result = []
        for doc, score in filter_knn_result.items():
            if doc in filter_inverted_result.keys():
                combine_result.append({ "doc" : doc, "score" : score })

        return combine_result
    
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

        final_prompt = qa_knowledge_prompt_build(query_input, recall_knowledge, A_Role, B_Role)
    else:
        query_type = QueryType.Conversation
        free_chat_coversions = [ item for item in session_history if item[2] == "QueryType.Conversation" ]
        final_prompt = conversion_prompt_build(query_input, free_chat_coversions[-2:], A_Role, B_Role)

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
            answer = Generate(sm_client, llm_model_endpoint, prompt=final_prompt, llm_name=llm_model_name, stop=STOP)
            
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
    update_session(session_id=session_id, question=query_input, answer=answer, intention=str(query_type))
    elpase_time = time.time() - start
    elpase_time1 = time.time() - start1
    logger.info(f'runing time of update_session : {elpase_time}s seconds')
    logger.info(f'runing time of all  : {elpase_time1}s seconds')

    return answer


@handle_error
def lambda_handler(event, context):

    # "model": 模型的名称
    # "chat_name": 对话标识，后端用来存储查找实现多轮对话 session
    # "prompt": 用户输入的问题
    # "max_tokens": 2048
    # "temperature": 0.9
    logger.info(f"event:{event}")
    # input_json = json.loads(event['body'])
    session_id = event['chat_name']
    question = event['prompt']
    model_name = event['model']
    embedding_endpoint = event['embedding_model'] 

    # model_name = 'chatglm-7b'
    llm_endpoint = None
    if model_name == 'chatglm':
        llm_endpoint = os.environ.get('llm_{}_endpoint'.format(model_name))
    elif model_name == 'bloomz': 
        llm_endpoint =  os.environ.get('llm_{}_endpoint'.format(model_name))
    elif model_name == 'llama':
        llm_endpoint =  os.environ.get('llm_{}_endpoint'.format(model_name))
        pass
    elif model_name == 'alpaca':
        llm_endpoint =  os.environ.get('llm_{}_endpoint'.format(model_name))
        pass
    else:
        llm_endpoint = os.environ.get('llm_default_endpoint')
        pass

    # 获取当前时间戳
    request_timestamp = time.time()  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    logger.info(f'request_timestamp :{request_timestamp}')
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")

    # 创建日志组和日志流
    log_group_name = '/aws/lambda/{}'.format(context.function_name)
    log_stream_name = context.aws_request_id
    client = boto3.client('logs')
    # 接收触发AWS Lambda函数的事件
    logger.info('The main brain has been activated, aws🚀!')

    # 1. 获取环境变量

    # embedding_endpoint = os.environ.get("embedding_endpoint", "")
    aos_endpoint = os.environ.get("aos_endpoint", "")
    aos_index = os.environ.get("aos_index", "")
    aos_knn_field = os.environ.get("aos_knn_field", "")
    aos_result_num = int(os.environ.get("aos_results", ""))

    Kendra_index_id = os.environ.get("Kendra_index_id", "")
    Kendra_result_num = int(os.environ.get("Kendra_result_num", ""))
    # Opensearch_result_num = int(os.environ.get("Opensearch_result_num", ""))

    logger.info(f'model_name : {model_name}')
    logger.info(f'llm_endpoint : {llm_endpoint}')
    logger.info(f'embedding_endpoint : {embedding_endpoint}')
    logger.info(f'aos_endpoint : {aos_endpoint}')
    logger.info(f'aos_index : {aos_index}')
    logger.info(f'aos_knn_field : {aos_knn_field}')
    logger.info(f'aos_result_num : {aos_result_num}')
    logger.info(f'Kendra_index_id : {Kendra_index_id}')
    logger.info(f'Kendra_result_num : {Kendra_result_num}')
    
    main_entry_start = time.time()  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    answer = main_entry(session_id, question, embedding_endpoint, llm_endpoint, model_name, aos_endpoint, aos_index, aos_knn_field, aos_result_num,
                       Kendra_index_id, Kendra_result_num)
    main_entry_elpase = time.time() - main_entry_start  # 或者使用 time.time_ns() 获取纳秒级别的时间戳
    logger.info(f'runing time of main_entry : {main_entry_elpase}s seconds')
    # 2. return rusult

    # 处理

    # Response:
    # "id": "设置一个uuid"
    # "created": "1681891998"
    # "model": "模型名称"
    # "choices": [{"text": "模型回答的内容"}]
    # "usage": {"prompt_tokens": 58, "completion_tokens": 15, "total_tokens": 73}}]

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': [{"id": str(uuid.uuid4()),
                             "created": request_timestamp,
                             "useTime": time.time() - request_timestamp,
                             "model": "main_brain",
                             "choices":
                             [{"text": answer}],
                             "usage": {"prompt_tokens": 58, "completion_tokens": 15, "total_tokens": 73}},
                            # {"id": uuid.uuid4(),
                            #  "created": request_timestamp,
                            #  "useTime": int(time.time()) - request_timestamp,
                            #  "model": "模型名称",
                            #  "choices":
                            #  [{"text": "2 模型回答的内容"}],
                            #  "usage": {"prompt_tokens": 58, "completion_tokens": 15, "total_tokens": 73}}
                            ]
    }


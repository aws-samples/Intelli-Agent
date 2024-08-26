import __main__
from datetime import datetime
import hashlib
import json
import os
import re
import time
from aiohttp import ClientError
import boto3
from openpyxl import load_workbook
from io import BytesIO
from botocore.paginate import TokenEncoder
from opensearchpy import RequestError, helpers
import logging
# from requests.auth import HTTPBasicAuth
from langchain.embeddings.bedrock import BedrockEmbeddings
# from opensearchpy.exceptions import BulkIndexError
# from common_logic.common_utils.logger_utils import get_logger

from aos.aos_utils import LLMBotOpenSearchClient
from constant import AOS_INDEX, BULK_SIZE, DEFAULT_CONTENT_TYPE, DEFAULT_MAX_ITEMS, DEFAULT_SIZE, EXECUTION_RESOURCE, PRESIGNED_URL_RESOURCE, SECRET_NAME

logger = logging.getLogger(__name__)
encoder = TokenEncoder()

s3_bucket_name = os.environ.get("S3_BUCKET")
aos_endpoint = os.environ.get("AOS_ENDPOINT", "")
region = os.environ.get("REGION", "us-east-1")
aos_domain_name = os.environ.get("AOS_DOMAIN_NAME", "smartsearch")
aos_secret = os.environ.get("AOS_SECRET_NAME", "opensearch-master-user")
intention_table_name = os.getenv("INTENTION_TABLE_NAME","intention")
dynamodb_resource = boto3.resource("dynamodb")
intention_table = dynamodb_resource.Table(intention_table_name)

sm_client = boto3.client("secretsmanager")
master_user = sm_client.get_secret_value(SecretId=aos_secret)["SecretString"]
secret_body = sm_client.get_secret_value(SecretId=SECRET_NAME)['SecretString']
secret = json.loads(secret_body)
username = secret.get("username")
password = secret.get("password")

if not aos_endpoint:
    opensearch_client = boto3.client("opensearch")
    response = opensearch_client.describe_domain(DomainName=aos_domain_name)
    aos_endpoint = response["DomainStatus"]["Endpoint"]

dynamodb_client = boto3.client("dynamodb")
s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime",region_name=region)
aos_client = LLMBotOpenSearchClient(aos_endpoint, (username, password)).client

# aos_client = OpenSearch(
#         hosts = [{'host': aos_endpoint, 'port': HTTPS_PORT_NUMBER}],
#         http_auth = HTTPBasicAuth(username,password),
#         use_ssl = True,
#         verify_certs = True,
#         connection_class = RequestsHttpConnection
    # )

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}

def lambda_handler(event, context):
    logger.info(event)
    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        email = claims["email"]
        cognito_groups = claims["cognito:groups"]
        cognito_groups_list = cognito_groups.split(",")
    else:
        email = event["multiValueHeaders"]["author"][0]
        cognito_groups_list = ["Admin"]
    #     group_name = claims["cognito:groups"] #Agree to only be in one group
    # else:
    #     group_name = "Admin"
    http_method = event["httpMethod"]
    resource:str = event["resource"]
    chatbot_id = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
    if resource == PRESIGNED_URL_RESOURCE:
        input_body = json.loads(event["body"])
        file_name = f"intentions/{chatbot_id}/[{input_body['timestamp']}]{input_body['file_name']}"
        presigned_url = __gen_presigned_url(file_name, 
                                     input_body.get("content_type", DEFAULT_CONTENT_TYPE),
                                     input_body.get("expiration", 60*60))
        output = {
            "message": "The S3 presigned url is generated",
            "data": {
                "url": presigned_url,
                "s3Bucket": s3_bucket_name,
                "s3Prefix": file_name,
            },
         
        }
    elif resource.startswith(EXECUTION_RESOURCE):
        if http_method == "POST":
            output = __create_execution(event, context, email)
        else:
            if resource == EXECUTION_RESOURCE:
                output = __list_execution(event)
            else:
                # executionId = resource.split("/").pop()
                output = __get_execution(event)
    try:
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }

def __get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value

def __gen_presigned_url(object_name: str, content_type: str, expiration: int):
    return s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": s3_bucket_name, "Key": object_name, "ContentType": content_type},
        ExpiresIn=expiration,
        HttpMethod="PUT",
    )


def __list_execution(event):
    max_items = __get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = __get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = __get_query_parameter(event, "StartingToken")
    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }
    response = dynamodb_client.scan(TableName=intention_table_name)
    output = {}
    page_json = []
    items = response['Items']

    # 处理分页
    while 'LastEvaluatedKey' in response:
        response = dynamodb_client.scan(
            TableName=intention_table_name,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])

    for item in items:
        item_json = {}
        for key in list(item.keys()):
            value = item.get(key, {"S": ""}).get("S","-")
            if key == "File":
                item_json["fileName"] = value.split("/").pop()
            elif key == "modelId":
                item_json["model"] = value
            elif key == "groupName":
                item_json["chatbotId"] = value
            elif key == "LastModifiedTime":
                item_json["createTime"] = value
            elif key == "LastModifiedBy":
                item_json["createBy"] = value
            elif key == "intentionId":
                item_json["executionId"] = value
            else:
                item_json[key] = value
            item_json["executionStatus"] = "COMPLETED"
        page_json.append(item_json)
        output["Items"] = page_json
    output["Config"] = config
    output["Count"] = len(items)
    return output


def __create_execution(event, context, email):
    input_body = json.loads(event["body"])
    execution_detail = {}
    execution_detail["tableItemId"] = context.aws_request_id
    execution_detail["chatbotId"] = input_body.get("chatbotId")
    execution_detail["index"] = input_body.get("index") if input_body.get("index") else f'{input_body.get("chatbotId")}-default-index'
    execution_detail["model"] = input_body.get("model")
    execution_detail["fileName"] = input_body.get("s3Prefix").split("/").pop()
    execution_detail["tag"] = input_body.get("tag") if input_body.get("tag") else f'{input_body.get("chatbotId")}-default-tag'
    # write to ddb(meta data)
    intention_table.put_item(
        Item={
            "groupName": execution_detail["chatbotId"],
            "intentionId": context.aws_request_id,
            "model": execution_detail["model"],
            "index": execution_detail["index"],
            "tag": execution_detail["tag"],
            "File": f'{input_body.get("s3Bucket")}{input_body.get("s3Prefix")}',
            "LastModifiedBy": email,
            "LastModifiedTime": re.findall(r'\[(.*?)\]', input_body.get("s3Prefix"))[0],
        }
    )
    # intention_table_name.put_item(Item=input_body)

    # write to aos(vectorData)
    __save_2_aos(input_body.get("s3Bucket"), input_body.get("s3Prefix"), input_body.get("model"), execution_detail["index"],context.aws_request_id)

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": execution_detail["tableItemId"],
                "input_payload": json.dumps(execution_detail),
                "result": "success"
            }
        ),
    }

def __save_2_aos(bucket: str, prefix: str, modelId: str, index: str, executionId: str):
    index_prefix="amazon-titan"
    if modelId.startswith('cohere'):
        index_prefix="cohere"
    # 检查索引是否存在
    index_exists = aos_client.indices.exists(index=f'{index_prefix}-{index}')
    if not index_exists:
        __create_index(f'{index_prefix}-{index}')
    __refresh_index(f'{index_prefix}-{index}', bucket, prefix, modelId,executionId)


def __create_index(index: str):
    body = {
        "settings" : {
            "index":{
                "number_of_shards" : 1,
                "number_of_replicas" : 0,
                "knn": True,
                "knn.algo_param.ef_search": 32
            }
        },
        "mappings": {
            "properties": {
                "text" : {
                    "type" : "text"
                },
                "sentence_vector" : {
                    "type" : "knn_vector",
                    "dimension" : 1024 if index.startswith("cohere") else 1536,
                    "method" : {
                        "engine" : "nmslib",
                        "space_type" : "l2",
                        "name" : "hnsw",
                        "parameters" : {
                        "ef_construction" : 512,
                        "m" : 16
                        }
                    }
                }
            }
        }
    }
    try:
        aos_client.indices.create(index=index, body=body)
        print(f"Index {index} created successfully.")
    except RequestError as e:
        print(f"====={e.error}")
    

def __refresh_index(index: str, bucket: str, prefix: str, modelId: str, executionId: str):
    # Open the file and read its contents
    response = __get_s3_object_with_retry(bucket, prefix)
    # response = s3_client.get_object(Bucket=bucket, Key=prefix)
    file_content = response['Body'].read()
    # 使用 pandas 读取 Excel 文件内容
    excel_file = BytesIO(file_content)
    # df = pd.read_excel(excel_file)
    workbook = load_workbook(excel_file)
    sheet = workbook.active
    success, failed = helpers.bulk(aos_client,  __append_embeddings(index, modelId, sheet, executionId), chunk_size=BULK_SIZE)
    aos_client.indices.refresh(index=index)
    print(f"Successfully added: {success} ")
    print(f"Failed: {len(failed)} ")

def  __append_embeddings(index, modelId, sheet, executionId):
    documents = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        question, answer, kwargs = row[0], row[1], row[2] if len(row) > 2 else None
        print(f"- Column 1: {question}, Column 2: {answer}, Column 3: {kwargs}")
        # embeddings_vectors = get_embedding(question)
        embedding_func = BedrockEmbeddings(
            client=bedrock_client,
            model_id=modelId,
            normalize=True
        )
        
        embeddings_vectors = embedding_func.embed_documents(
            [question]
        )
        documents.append(
                    { 
                        "text" : question,
                        "metadata" : {
                            "executionId": executionId,
                            "answer": answer,
                            "source": "portal",
                            "kwargs": kwargs,
                            "type": "Intent"
                            },
                        "sentence_vector" : embeddings_vectors[0]
                    }
                )
        for document in documents:
            yield {"_op_type": "index", "_index": index, "_source": document, "_id": hashlib.md5(str(document).encode('utf-8')).hexdigest()}


def __get_execution(event):
    executionId = event.get("path", "").split("/").pop()
    # 设置过滤条件
    filter_expression = "attribute_exists(intentionId) AND intentionId = :value"

    # 执行 scan 操作
    response = dynamodb_client.scan(
        TableName=intention_table_name,
        FilterExpression=filter_expression,
        ExpressionAttributeValues={
            ":value": {"S": executionId}  # 替换为你的实际值
        }
    )

    # 获取结果
    items = response['Items']
    res = {}
    Items = []
    for item in items:
        item_json = {}
        for key in list(item.keys()):
            model = item.get("model", {"S": ""}).get("S","-")
            index = item.get("index", {"S": ""}).get("S","-")
            value = item.get(key, {"S": ""}).get("S","-")
            if key == "File":
                split_index = value.rfind('/')
                if split_index != -1:
                    item_json["s3Path"] = value[:split_index]
                    item_json["s3Prefix"] = value[split_index + 1:]
                else:
                    item_json["s3Path"] = value
                    item_json["s3Prefix"] = "-"
            elif key == "LastModifiedTime":
                item_json["createTime"] = value
            else:
                continue
            item_json["status"] = "COMPLETED"
            item_json["QAList"] = __retrieve_source_from_aos(model, index, executionId)
        Items.append(item_json)
    res["Items"] = Items
    res["Count"] = len(items)
    return res

def __get_s3_object_with_retry(bucket: str, key: str, max_retries: int = 5, delay: int = 1):
    attempt = 0
    while attempt < max_retries:
        try:
            # 尝试获取 S3 对象
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response
        except Exception as e:
            print(f'------{type(e)}')
            # 打印错误信息（可选）
            print(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt >= max_retries:
                # 如果超过最大重试次数，则抛出异常
                print("Time out, retry...")
                raise 
            # 等待指定时间后重试
            time.sleep(delay)

def __retrieve_source_from_aos(model: str, index: str, executionId: str):
    index_prefix="amazon-titan"
    if model.startswith('cohere'):
        index_prefix="cohere"
    # 执行查询，返回所有文档的 _source 字段
    response = aos_client.search(index=f"{index_prefix}-{index}", body={
        "_source": True,  # 只返回 _source 字段
        "query": {
            "match_all": {}
        }
    })
    res = []
    # 打印所有文档的 _source 字段
    for item in response["hits"]["hits"]: 
        source = item["_source"]
        metadata = source["metadata"]
        if metadata["executionId"]== executionId:
            res.append({
               "question": source["text"],
               "intention": source["metadata"]["answer"],
               "kwargs": source["metadata"]["kwargs"]
            })
    return res

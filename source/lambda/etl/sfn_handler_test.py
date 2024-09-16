import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from utils.parameter_utils import get_query_parameter

import boto3
from constant import IndexTag, IndexType
from utils.ddb_utils import initiate_chatbot, initiate_index, initiate_model

os.environ['AWS_REGION'] = 'us-west-2'
os.environ['EXECUTION_TABLE_NAME'] = 'ai-customer-service-knowledgebasestackNestedStackknowledgebasestackNestedStackResource-1G2D70WWWAQHW-Execution67854D3B-1WKWDMDSPC9G'
os.environ['INDEX_TABLE_NAME'] = 'ai-customer-service-sharedconstructIndexC12FA5A4-1PP0Y2H27W1FG'
os.environ['CHATBOT_TABLE_NAME'] = 'ai-customer-service-sharedconstructChatbotF9A1CE94-1BQ1AHO51CCKV'
os.environ['MODEL_TABLE_NAME'] = 'ai-customer-service-sharedconstructModelFA5EA0DE-TZVYZXHK1KCK'
os.environ['EMBEDDING_ENDPOINT'] = 'bce-embedding-and-bge-reranker-43972-endpoint'
os.environ['sfn_arn'] = 'arn:aws:states:us-west-2:817734611975:stateMachine:ETLStateA5DEA10E-Vj8Gel9CgSSw'
test_context_id = "34463aa6-d79b-45d1-ac3b-1981709d4e07"


client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE_NAME"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
create_time = str(datetime.now(timezone.utc))
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    # Check the event for possible S3 created event
    input_payload = {}
    logger.info(event)
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        if "use_api_key" in claims:
            group_name = get_query_parameter(event, "GroupName", "Admin")
            cognito_groups_list = [group_name]
        else:
            cognito_groups = claims["cognito:groups"]
            cognito_groups_list = cognito_groups.split(",")
    else:
        logger.error("Invalid authorizer type")
        return {
            "statusCode": 403,
            "headers": resp_header,
            "body": json.dumps({"error": "Invalid authorizer type"}),
        }

    # Parse the body from the event object
    input_body = json.loads(event["body"])
    if "indexType" not in input_body or input_body["indexType"] not in [
        IndexType.QD.value,
        IndexType.QQ.value,
        IndexType.INTENTION.value,
    ]:
        return {
            "statusCode": 400,
            "headers": resp_header,
            "body": (
                f"Invalid indexType, valid values are "
                f"{IndexType.QD.value}, {IndexType.QQ.value}, "
                f"{IndexType.INTENTION.value}"
            ),
        }
    index_type = input_body["indexType"]
    group_name = (
        "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
    )
    chatbot_id = input_body.get("chatbotId", group_name.lower())

    if "indexId" in input_body:
        index_id = input_body["indexId"]
    else:
        # Use default index id if not specified in the request
        index_id = f"{chatbot_id}-qd-default"
        if index_type == IndexType.QQ.value:
            index_id = f"{chatbot_id}-qq-default"
        elif index_type == IndexType.INTENTION.value:
            index_id = f"{chatbot_id}-intention-default"

    if "tag" in input_body:
        tag = input_body["tag"]
    else:
        tag = index_id

    input_body["indexId"] = index_id
    input_body["groupName"] = (
        group_name if "groupName" not in input_body else input_body["groupName"]
    )

    model_id = f"{chatbot_id}-embedding"
    embedding_model_type = initiate_model(
        model_table, group_name, model_id, embedding_endpoint, create_time
    )
    initiate_index(
        index_table, group_name, index_id, model_id, index_type, tag, create_time
    )
    initiate_chatbot(
        chatbot_table, group_name, chatbot_id, index_id, index_type, tag, create_time
    )

    input_body["tableItemId"] = test_context_id
    input_body["chatbotId"] = chatbot_id
    input_body["embeddingModelType"] = embedding_model_type
    input_payload = json.dumps(input_body)
    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=input_payload
    )

    # Update execution table item
    if "tableItemId" in input_body:
        del input_body["tableItemId"]
    execution_id = response["executionArn"].split(":")[-1]
    input_body["sfnExecutionId"] = execution_id
    input_body["executionStatus"] = "IN-PROGRESS"
    input_body["indexId"] = index_id
    input_body["executionId"] = test_context_id
    input_body["uiStatus"] = "ACTIVE"
    input_body["createTime"] = create_time

    execution_table.put_item(Item=input_body)

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": test_context_id,
                "step_function_arn": response["executionArn"],
                "input_payload": input_payload,
            }
        ),
    }


event = {
	'resource': '/knowledge-base/executions',
	'path': '/knowledge-base/executions',
	'httpMethod': 'POST',
	'headers': {
		'accept': 'application/json, text/plain, */*',
		'accept-encoding': 'gzip, deflate, br, zstd',
		'accept-language': 'en,zh-CN;q=0.9,zh;q=0.8,pt;q=0.7,tr;q=0.6,pl;q=0.5,ar;q=0.4',
		'Authorization': 'Bearer eyJraWQiOiI0SExrTmhKcDdDSDF0YkJLa2hraVAyZDZVQ1dudEJYUUJhNkVWaFFxZXpVPSIsImFsZyI6IlJTMjU2In0.eyJhdF9oYXNoIjoidnVWeTNDU0tNMnNTY1BuSG43aXJXQSIsInN1YiI6IjM4MTFlMzYwLWMwYjEtNzBhMS0zY2ExLTE2ZTM3OGJmYjU1MSIsImNvZ25pdG86Z3JvdXBzIjpbIkFkbWluIl0sImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtd2VzdC0yLmFtYXpvbmF3cy5jb21cL3VzLXdlc3QtMl9Nc203akYxSzEiLCJjb2duaXRvOnVzZXJuYW1lIjoiMzgxMWUzNjAtYzBiMS03MGExLTNjYTEtMTZlMzc4YmZiNTUxIiwib3JpZ2luX2p0aSI6Ijg0MjgxZmQ4LTg5NTEtNDg4Zi05OWRhLWM1NTBmYTc3MTdkMCIsImF1ZCI6IjZqZnZyMmx1Ym5jZmJrb29pZWs5OWZpYXVqIiwiZXZlbnRfaWQiOiI5YmY2M2IxNC1kMDVjLTQ2MTItYWY5Ny02YjM0OTVhNThmNTIiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTcyNjM1NzY3NywiZXhwIjoxNzI2MzYxMjc3LCJpYXQiOjE3MjYzNTc2NzcsImp0aSI6IjBlNTJlMTdiLWNiN2ItNDY1OC1iZGNjLTMzZGE3YjBjMGQwZCIsImVtYWlsIjoibHZuaW5nQGFtYXpvbi5jb20ifQ.ecG_RDNsr-sLyY-FaFT4n9lm1fMawKkb7WphjPCZmLLYFZJbO9MjNPbH66AoaK1e1hImev-46EBRq48WnJKdjYBb3FwSe-G0nZQFxNqHXXHdPvoziVVgZhRlX1INc1e4Q9DVByaXFQc-Z1p0q1RdqLsvC0N53J5Nb7OLpDwE5B4pxtleO9sFzdiGtl0OtpCsWDmE3zq8PmeU_96T2NWb6ghY_HetWOP3k-1tT5Rv3Q8ep3kHGqrWWyfIDyyXLS_pGEIJJ3gqQEyyPefE53jiJnVRC_3-xTFt46Vie7aqLhT0VTjR5A03QV9OAhafjUUXv2Ro3daQkZJQumn2OgHtNQ',
		'cache-control': 'no-cache',
		'content-type': 'application/json',
		'Host': 'qrm62mch17.execute-api.us-west-2.amazonaws.com',
		'origin': 'https://d10an0sufgcu0k.cloudfront.net',
		'pragma': 'no-cache',
		'priority': 'u=1, i',
		'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
		'sec-ch-ua-mobile': '?0',
		'sec-ch-ua-platform': '"macOS"',
		'sec-fetch-dest': 'empty',
		'sec-fetch-mode': 'cors',
		'sec-fetch-site': 'cross-site',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
		'X-Amzn-Trace-Id': 'Root=1-66e620fc-5af4815316e6a1fc136b7077',
		'X-Forwarded-For': '205.251.233.105',
		'X-Forwarded-Port': '443',
		'X-Forwarded-Proto': 'https'
	},
	'multiValueHeaders': {
		'accept': ['application/json, text/plain, */*'],
		'accept-encoding': ['gzip, deflate, br, zstd'],
		'accept-language': ['en,zh-CN;q=0.9,zh;q=0.8,pt;q=0.7,tr;q=0.6,pl;q=0.5,ar;q=0.4'],
		'Authorization': ['Bearer eyJraWQiOiI0SExrTmhKcDdDSDF0YkJLa2hraVAyZDZVQ1dudEJYUUJhNkVWaFFxZXpVPSIsImFsZyI6IlJTMjU2In0.eyJhdF9oYXNoIjoidnVWeTNDU0tNMnNTY1BuSG43aXJXQSIsInN1YiI6IjM4MTFlMzYwLWMwYjEtNzBhMS0zY2ExLTE2ZTM3OGJmYjU1MSIsImNvZ25pdG86Z3JvdXBzIjpbIkFkbWluIl0sImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtd2VzdC0yLmFtYXpvbmF3cy5jb21cL3VzLXdlc3QtMl9Nc203akYxSzEiLCJjb2duaXRvOnVzZXJuYW1lIjoiMzgxMWUzNjAtYzBiMS03MGExLTNjYTEtMTZlMzc4YmZiNTUxIiwib3JpZ2luX2p0aSI6Ijg0MjgxZmQ4LTg5NTEtNDg4Zi05OWRhLWM1NTBmYTc3MTdkMCIsImF1ZCI6IjZqZnZyMmx1Ym5jZmJrb29pZWs5OWZpYXVqIiwiZXZlbnRfaWQiOiI5YmY2M2IxNC1kMDVjLTQ2MTItYWY5Ny02YjM0OTVhNThmNTIiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTcyNjM1NzY3NywiZXhwIjoxNzI2MzYxMjc3LCJpYXQiOjE3MjYzNTc2NzcsImp0aSI6IjBlNTJlMTdiLWNiN2ItNDY1OC1iZGNjLTMzZGE3YjBjMGQwZCIsImVtYWlsIjoibHZuaW5nQGFtYXpvbi5jb20ifQ.ecG_RDNsr-sLyY-FaFT4n9lm1fMawKkb7WphjPCZmLLYFZJbO9MjNPbH66AoaK1e1hImev-46EBRq48WnJKdjYBb3FwSe-G0nZQFxNqHXXHdPvoziVVgZhRlX1INc1e4Q9DVByaXFQc-Z1p0q1RdqLsvC0N53J5Nb7OLpDwE5B4pxtleO9sFzdiGtl0OtpCsWDmE3zq8PmeU_96T2NWb6ghY_HetWOP3k-1tT5Rv3Q8ep3kHGqrWWyfIDyyXLS_pGEIJJ3gqQEyyPefE53jiJnVRC_3-xTFt46Vie7aqLhT0VTjR5A03QV9OAhafjUUXv2Ro3daQkZJQumn2OgHtNQ'],
		'cache-control': ['no-cache'],
		'content-type': ['application/json'],
		'Host': ['qrm62mch17.execute-api.us-west-2.amazonaws.com'],
		'origin': ['https://d10an0sufgcu0k.cloudfront.net'],
		'pragma': ['no-cache'],
		'priority': ['u=1, i'],
		'sec-ch-ua': ['"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'],
		'sec-ch-ua-mobile': ['?0'],
		'sec-ch-ua-platform': ['"macOS"'],
		'sec-fetch-dest': ['empty'],
		'sec-fetch-mode': ['cors'],
		'sec-fetch-site': ['cross-site'],
		'User-Agent': ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'],
		'X-Amzn-Trace-Id': ['Root=1-66e620fc-5af4815316e6a1fc136b7077'],
		'X-Forwarded-For': ['205.251.233.105'],
		'X-Forwarded-Port': ['443'],
		'X-Forwarded-Proto': ['https']
	},
	'queryStringParameters': None,
	'multiValueQueryStringParameters': None,
	'pathParameters': None,
	'stageVariables': None,
	'requestContext': {
		'resourceId': 'b6pi3o',
		'authorizer': {
			'claims': '{"at_hash": "vuVy3CSKM2sScPnHn7irWA", "sub": "3811e360-c0b1-70a1-3ca1-16e378bfb551", "cognito:groups": "Admin", "email_verified": true, "iss": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_Msm7jF1K1", "cognito:username": "3811e360-c0b1-70a1-3ca1-16e378bfb551", "origin_jti": "84281fd8-8951-488f-99da-c550fa7717d0", "aud": "6jfvr2lubncfbkooiek99fiauj", "event_id": "9bf63b14-d05c-4612-af97-6b3495a58f52", "token_use": "id", "auth_time": 1726357677, "exp": 1726361277, "iat": 1726357677, "jti": "0e52e17b-cb7b-4658-bdcc-33da7b0c0d0d", "email": "lvning@amazon.com"}',
			'principalId': 'me',
			'integrationLatency': 0,
			'authorizerType': 'lambda_authorizer'
		},
		'resourcePath': '/knowledge-base/executions',
		'httpMethod': 'POST',
		'extendedRequestId': 'eHoXjGXzvHcEpCQ=',
		'requestTime': '14/Sep/2024:23:49:16 +0000',
		'path': '/prod//knowledge-base/executions',
		'accountId': '817734611975',
		'protocol': 'HTTP/1.1',
		'stage': 'prod',
		'domainPrefix': 'qrm62mch17',
		'requestTimeEpoch': 1726357756805,
		'requestId': '6d4d683f-c2a5-4a44-a0f8-0323eb3e0eaa',
		'identity': {
			'cognitoIdentityPoolId': None,
			'accountId': None,
			'cognitoIdentityId': None,
			'caller': None,
			'sourceIp': '205.251.233.105',
			'principalOrgId': None,
			'accessKey': None,
			'cognitoAuthenticationType': None,
			'cognitoAuthenticationProvider': None,
			'userArn': None,
			'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
			'user': None
		},
		'domainName': 'qrm62mch17.execute-api.us-west-2.amazonaws.com',
		'deploymentId': '4i3hi3',
		'apiId': 'qrm62mch17'
	},
	'body': '{"s3Bucket":"ai-customer-service-apiconstructllmbotdocumentsfc4-pwgby9vcdwyx","s3Prefix":"documents/Admin/blog.docx","offline":"true","qaEnhance":"false","chatbotId":"admin","indexType":"qd","operationType":"create"}',
	'isBase64Encoded': False
}


context = {
    "aws_request_id": "34463aa6-d79b-45d1-ac3b-1981709d4e07"
}
handler(event, context)

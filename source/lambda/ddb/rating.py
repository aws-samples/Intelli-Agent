from datetime import datetime
import json
import boto3
import os
import uuid
import logging
from decimal import Decimal
from botocore.exceptions import ClientError

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)

"""
Sample Item:
{'UserId': '268b8afa-3d5a-4147-9707-1975415a1732', 
'History': [{'type': 'human', 'data': {'type': 'human', 'content': 'Hi', 'additional_kwargs': {}, 'example': False}}, 
{'type': 'ai', 'data': {'type': 'ai', 'content': ' Hello!', 'additional_kwargs': {'mode': 'chain', 'modelKwargs': {'maxTokens': Decimal('512'), 'temperature': Decimal('0.6'), 'streaming': True, 'topP': Decimal('0.9')}, 'modelId': 'anthropic.claude-v2', 'documents': [], 'sessionId': 'cc8700e8-f8ea-4f43-8951-964d813e5a96', 'userId': '268b8afa-3d5a-4147-9707-1975415a1732', 'prompts': [['\n\nHuman: The following is a friendly conversation between a human and an AI. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\n\nQuestion: Hi\n\nAssistant:']]}, 'example': False}}], 
'SessionId': 'cc8700e8-f8ea-4f43-8951-964d813e5a96', 
'StartTime': '2023-12-25T06:52:42.618249'}
"""

def convert_to_langchain_format(openai_message):
    """
    Sample openai_message:
    {
        "role": "assistant",
        "content": "您可以在SSML标记语言中直接嵌入发音,以指定Polly如何朗读密码中的大小写...",
        "knowledge_sources": [
            "https://random_utl/index.html"
        ]
    }
    """
    message_type = openai_message['role']
    message_content = openai_message['content']
    message_sources = openai_message.get('knowledge_sources', [])
    additional_kwargs = {'knowledge_sources': message_sources} if message_sources else {}

    converted_message = {
        'type': 'human',
        'data': {
            'type': message_type,
            'content': message_content,
            'additional_kwargs': additional_kwargs,
            'example': False
        }
    }
    return converted_message

def get_session(table, session_id, user_id):
    response = {}
    try:
        response = table.get_item(Key={"SessionId": session_id, "UserId": user_id})
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print("No record found with session id: %s", session_id)
        else:
            print(error)
    
    return response.get("Item", {})

# SESSIONS_BY_USER_ID_INDEX_NAME = "byUserId"
def list_sessions_by_user_id(table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME):
    response = {}
    try:
        response = table.query(
            KeyConditionExpression="UserId = :user_id",
            ExpressionAttributeValues={":user_id": user_id},
            IndexName=SESSIONS_BY_USER_ID_INDEX_NAME,
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print("No record found for user id: %s", user_id)
        else:
            print(error)

    return response.get("Items", [])

def add_messages(table, session_id, user_id, messages):
    """Append the message to the record in DynamoDB"""
    response = {}

    try:
        response = table.put_item(
            Item={
                "SessionId": session_id,
                "UserId": user_id,
                "StartTime": datetime.now().isoformat(),
                "History": messages,
            }
        )
        response = {"added": True}
    except ClientError as err:
        print(err)
        response = {"added": False, "error": str(err)}
    
    return response
    
    

def add_metadata(table, session_id, user_id, metadata, message_id = -1):
    """Add additional metadata to the last message"""
    response = {}

    session = get_session(table, session_id, user_id)
    messages = session.get("History", [])
    start_time = session.get("StartTime", "")

    if not messages:
        return {"added" : False, "error": "Failed to add metadata. No messages found in session."}

    metadata = json.loads(json.dumps(metadata), parse_float=Decimal)
    messages[message_id]["data"]["additional_kwargs"] = metadata

    try:
        table.put_item(
            Item={
                "SessionId": session_id,
                "UserId": user_id,
                "StartTime": start_time,
                "History": messages,
            }
        )
        response = {"added": True}

    except Exception as err:
        print(err)
        response = {"added": False, "error": str(err)}
    
    return response

def add_feedback(table, session_id, user_id, feedback_message_id, output_messages, feedback) -> None:
    """
    Sample feedback:
    {
        "type" : "thumbs_down",
        "suggest_message" :  {
            "role": "user",
            "content": "标准回答, abc..",
        }
    }
    """

    session = get_session(table, session_id, user_id)
    messages = session.get("History", [])
    start_time = session.get("StartTime", "")

    if not messages:
        return {"added": False, "error": "Failed to add feedback. No messages found in session."}
    elif not output_messages and not feedback_message_id:
        return {"added": False, "error": "Failed to add feedback. Please specify the output_messages or the message_id in the request to add feedback."}
    
    message_content_for_feedback = output_messages[-1].get("content", "") if output_messages else ""

    for message in messages:
        
        ddb_message_id = message.get("data", {}).get("additional_kwargs", {}).get("message_id", "")
        ddb_message_content = message.get("data", {}).get("content", "")
        if feedback_message_id and ddb_message_id == feedback_message_id:
            message["data"]["additional_kwargs"]["feedback"] = feedback
            break
        elif message_content_for_feedback and ddb_message_content == message_content_for_feedback:
            message["data"]["additional_kwargs"]["feedback"] = feedback
            break

    try:
        table.put_item(
            Item={
                "SessionId": session_id,
                "UserId": user_id,
                "StartTime": start_time,
                "History": messages,
            }
        )
        response = {"added": True}

    except Exception as err:
        print(err)
        response = {"added": False, "error": str(err)}
    
    return response


def delete_session(table, session_id, user_id):
    try:
        table.delete_item(Key={"SessionId": session_id, "UserId": user_id})
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print("No record found with session id: %s", session_id)
        else:
            print(error)

        return {"deleted": False}

    return {"deleted": True}


def delete_user_sessions(table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME):
    sessions = list_sessions_by_user_id(table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME)
    ret_value = []

    for session in sessions:
        result = delete_session(table, session["SessionId"], user_id)
        ret_value.append({"id": session["SessionId"], "deleted": result["deleted"]})

    return ret_value

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.getenv('SESSIONS_TABLE_NAME')
    SESSIONS_BY_USER_ID_INDEX_NAME = os.getenv('SESSIONS_BY_USER_ID_INDEX_NAME')

    session_table = dynamodb.Table(table_name)

    http_method = event['httpMethod']
    body = json.loads(event['body'])

    required_fields = ["operation", "session_id"]
    
    if not all(field in body for field in required_fields):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Missing required fields'
            })
        }

    operation = body['operation']
    session_id = body['session_id']
    user_id = body.get('user_id', 'default_user_id')
    messages = body.get('messages', [])
    input_messages = body.get('input_messages', [])
    output_messages = body.get('output_messages', [])
    message_id = body.get('message_id', None)
    feedback = body.get('feedback', [])
    metadata = body.get('metadata', {})

    operations_mapping = {
        'POST': {
            'get_session': lambda: get_session(session_table, session_id, user_id),
            'list_sessions_by_user_id': lambda: list_sessions_by_user_id(session_table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME),
            'add_messages': lambda: add_messages(session_table, session_id, user_id, messages),
            'add_metadata': lambda: add_metadata(session_table, session_id, user_id, metadata),
            'add_feedback': lambda: add_feedback(session_table, session_id, user_id, message_id, output_messages, feedback),
            'delete_session': lambda: delete_session(session_table, session_id, user_id),
            'delete_user_sessions': lambda: delete_user_sessions(session_table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME)
        }
    }

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    
    try:
        if http_method in operations_mapping and operation in operations_mapping[http_method]:
            response = operations_mapping[http_method][operation]()
            logger.info("http_method: {}, operation: {}, response: {}".format(http_method, operation, response))
            return {
                'statusCode': 200,
                'headers': resp_header,
                'body': json.dumps(response)
            }
        else:
            raise Exception(f'Invalid {http_method} operation: {operation}')
    except Exception as e:
        # Return an error response
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
        
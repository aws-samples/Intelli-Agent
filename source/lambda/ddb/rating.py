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

def add_message(table, session_id, user_id, messages) -> None:
    """Append the message to the record in DynamoDB"""

    try:
        table.put_item(
            Item={
                "SessionId": session_id,
                "UserId": user_id,
                "StartTime": datetime.now().isoformat(),
                "History": messages,
            }
        )
    except ClientError as err:
        print(err)

def add_metadata(table, session_id, user_id, metadata) -> None:
    """Add additional metadata to the last message"""
    messages = get_session(table, session_id, user_id).get("History", [])
    if not messages:
        return

    metadata = json.loads(json.dumps(metadata), parse_float=Decimal)
    messages[-1]["data"]["additional_kwargs"] = metadata

    try:
        table.put_item(
            Item={
                "SessionId": session_id,
                "UserId": user_id,
                "StartTime": datetime.now().isoformat(),
                "History": messages,
            }
        )

    except Exception as err:
        print(err)

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

    required_fields = ["operation", "session_id", "user_id"]
    
    if not all(field in body for field in required_fields):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Missing required fields'
            })
        }

    operation = body['operation']
    session_id = body['session_id']
    user_id = body['user_id']
    messages = body.get('messages', [])
    metadata = body.get('metadata', {})

    operations_mapping = {
        'POST': {
            'get_session': lambda: get_session(session_table, session_id, user_id),
            'list_sessions_by_user_id': lambda: list_sessions_by_user_id(session_table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME),
            'add_message': lambda: add_message(session_table, session_id, user_id, messages),
            'add_metadata': lambda: add_metadata(session_table, session_id, user_id, metadata),
            'delete_session': lambda: delete_session(session_table, session_id, user_id),
            'delete_user_sessions': lambda: delete_user_sessions(session_table, user_id, SESSIONS_BY_USER_ID_INDEX_NAME)
        }
    }
    
    try:
        if http_method in operations_mapping and operation in operations_mapping[http_method]:
            response = operations_mapping[http_method][operation]()
            logger.info("http_method: {}, operation: {}, response: {}".format(http_method, operation, response))
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
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
        
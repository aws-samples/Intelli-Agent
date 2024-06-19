import json
import logging
import os
import time
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)


# Custom JSON encoder to handle decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)  # Convert decimal to string
        return super(DecimalEncoder, self).default(o)


"""
Sample Item:
{'userId': '268b8afa-3d5a-4147-9707-1975415a1732', 
'History': [{'type': 'human', 'data': {'type': 'human', 'content': 'Hi', 'additional_kwargs': {}, 'example': False}}, 
{'type': 'ai', 'data': {'type': 'ai', 'content': ' Hello!', 'additional_kwargs': {'mode': 'chain', 'modelKwargs': {'maxTokens': Decimal('512'), 'temperature': Decimal('0.6'), 'streaming': True, 'topP': Decimal('0.9')}, 'modelId': 'anthropic.claude-v2', 'documents': [], 'sessionId': 'cc8700e8-f8ea-4f43-8951-964d813e5a96', 'userId': '268b8afa-3d5a-4147-9707-1975415a1732', 'prompts': [['\n\nHuman: The following is a friendly conversation between a human and an AI. If the AI does not know the answer to a question, it truthfully says it does not know.\n\nCurrent conversation:\n\n\nQuestion: Hi\n\nAssistant:']]}, 'example': False}}], 
'sessionId': 'cc8700e8-f8ea-4f43-8951-964d813e5a96', 
'StartTime': '2023-12-25T06:52:42.618249'}
"""


def get_session(sessions_table, session_id, user_id):
    response = {}
    try:
        response = sessions_table.get_item(
            Key={"sessionId": session_id, "userId": user_id}
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print("No record found with session id: %s", session_id)
        else:
            print(error)

    return response.get("Item", {})


def get_message(messages_table, message_id, session_id):
    response = {}
    try:
        response = messages_table.get_item(
            Key={"messageId": message_id, "sessionId": session_id}
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print("No record found with message id: %s", message_id)
        else:
            print(error)

    return response.get("Item", {})


def add_feedback(
    sessions_table,
    messages_table,
    session_id,
    user_id,
    message_id,
    feedback_type,
    feedback_reason,
    suggest_message,
) -> None:
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

    message = get_message(messages_table, message_id, session_id)

    if not message:
        return {
            "added": False,
            "error": "Failed to add feedback. No messages found in session.",
        }

    try:
        current_timestamp = Decimal.from_float(time.time())
        messages_table.update_item(
            Key={"messageId": message_id, "sessionId": session_id},
            UpdateExpression="SET feedbackType = :ft, feedbackReason = :fr, suggestMessage = :sm, lastModifiedTimestamp = :t",
            ExpressionAttributeValues={
                ":ft": feedback_type,
                ":fr": feedback_reason,
                ":sm": suggest_message,
                ":t": current_timestamp,
            },
            ReturnValues="UPDATED_NEW",
        )
        sessions_table.update_item(
            Key={"sessionId": session_id, "userId": user_id},
            UpdateExpression="SET lastModifiedTimestamp = :t",
            ExpressionAttributeValues={":t": current_timestamp},
            ReturnValues="UPDATED_NEW",
        )
        response = {"added": True}

    except Exception as err:
        print(err)
        response = {"added": False, "error": str(err)}

    return response


def get_feedback(messages_table, message_id, session_id):
    message = get_message(messages_table, message_id, session_id)

    if message:
        return {
            "feedback_type": message.get("feedbackType", ""),
            "feedback_reason": message.get("feedbackReason", ""),
            "suggest_message": message.get("suggestMessage", ""),
        }
    else:
        return {}


def lambda_handler(event, context):
    dynamodb = boto3.resource("dynamodb")
    sessions_table_name = os.getenv("SESSIONS_TABLE_NAME")
    messages_table_name = os.getenv("MESSAGES_TABLE_NAME")

    sessions_table = dynamodb.Table(sessions_table_name)
    messages_table = dynamodb.Table(messages_table_name)

    http_method = event["httpMethod"]
    body = json.loads(event["body"])

    required_fields = ["operation"]

    if not all(field in body for field in required_fields):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing required fields"}),
        }

    operation = body["operation"]
    session_id = body.get("session_id", "")
    user_id = body.get("user_id", "default_user_id")
    message_id = body.get("message_id", None)
    feedback_type = body.get("feedback_type", None)
    feedback_reason = body.get("feedback_reason", None)
    suggest_message = body.get("suggest_message", None)

    operations_mapping = {
        "POST": {
            "get_session": lambda: get_session(sessions_table, session_id, user_id),
            "get_message": lambda: get_message(messages_table, message_id, session_id),
            "add_feedback": lambda: add_feedback(
                sessions_table,
                messages_table,
                session_id,
                user_id,
                message_id,
                feedback_type,
                feedback_reason,
                suggest_message,
            ),
            "get_feedback": lambda: get_feedback(
                messages_table, message_id, session_id
            ),
        }
    }

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        if (
            http_method in operations_mapping
            and operation in operations_mapping[http_method]
        ):
            response = operations_mapping[http_method][operation]()
            logger.info(
                "http_method: {}, operation: {}, response: {}".format(
                    http_method, operation, response
                )
            )
            return {
                "statusCode": 200,
                "headers": resp_header,
                "body": json.dumps(response, cls=DecimalEncoder),
            }
        else:
            raise Exception(f"Invalid {http_method} operation: {operation}")
    except Exception as e:
        # Return an error response
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

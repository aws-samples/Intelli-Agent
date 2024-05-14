import json
import os
import logging
import time
import uuid

import boto3
print(boto3.__version__)
import sys

# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR))
# sys.path.append(os.path.dirname(SCRIPT_DIR)+'/layer_logic')

from common_utils.ddb_utils import DynamoDBChatMessageHistory
from lambda_main.main_utils.online_entries import get_entry
from lambda_main.maing_utils.response_utils import process_response

# region = os.environ["AWS_REGION"]
embedding_endpoint = os.environ.get("embedding_endpoint", "")
aos_index = os.environ.get("aos_index", "")

sessions_table_name = os.environ.get("sessions_table_name", "")
messages_table_name = os.environ.get("messages_table_name", "")
websocket_url = os.environ.get("websocket_url", "")
ws_client = None


class APIException(Exception):
    def __init__(self, message, code: str = None):
        if code:
            super().__init__("[{}] {}".format(code, message))
        else:
            super().__init__(message)


def load_ws_client():
    global ws_client
    if ws_client is None:
        ws_client = boto3.client("apigatewaymanagementapi", endpoint_url=websocket_url)
    return ws_client


def handle_error(func):
    """Decorator for exception handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIException as e:
            # logger.exception(e)
            raise e
        except Exception as e:
            # logger.exception(e)
            raise RuntimeError(
                "Unknown exception, please check Lambda log for more details"
            )

    return wrapper


def _is_websocket_request(event):
    """Check if the request is WebSocket or Restful

    Args:
        event: lambda request event
    """
    if (
        "requestContext" in event
        and "eventType" in event["requestContext"]
        and event["requestContext"]["eventType"] == "MESSAGE"
    ):
        return True
    else:
        return False

# @handle_error
def lambda_handler(event, context):
    request_timestamp = time.time()
    print(f"request_timestamp :{request_timestamp}")
    print(f"event:{event}")
    print(f"context:{context}")
    if "Records" not in event:
        # Restful API invocation
        event["Records"] = [{"body": json.dumps(event)}]

    for record in event["Records"]:
        record_event = json.loads(record["body"])
        # Get request body
        event_body = json.loads(record_event["body"])
        # model = event_body['model']
        # session_id = event_body.get("session_id", None) or "N/A"
        messages = event_body.get("messages", [])
        # deal with stream parameter
        stream = _is_websocket_request(record_event)
        stream = False
        if stream:
            load_ws_client()

        # logger.info(f"stream decode: {stream}")
        client_type = event_body.get("client_type", "default_client_type")
        entry_type = event_body.get("type", Type.COMMON).lower()
        enable_debug = event_body.get("enable_debug", False)
        get_contexts = event_body.get("get_contexts", False)
        session_id = event_body.get("session_id", None)
        ws_connection_id = None

        debug_level = event_body.get("debug_level", logging.INFO)
        # logger.setLevel(debug_level)

        # if messages and entry_type != Type.MARKET_CONVERSATION_SUMMARY.value:
        #     # assert len(messages) == 1
        #     question = messages[-1]["content"]
        #     custom_message_id = messages[-1].get("custom_message_id", "")
        # else:
        #     question = ""  # MARKET_CONVERSATION_SUMMARY
        #     custom_message_id = event.get("custom_message_id", "")

        question = messages[-1]["content"]
        custom_message_id = messages[-1].get("custom_message_id", "")
        
        # custom_message_id 字段位置不合理
        # _, question = process_input_messages(messages)
        # role = "user"

        if not session_id:
            session_id = f"session_{int(request_timestamp)}"

        if stream:
            ws_connection_id = record_event["requestContext"]["connectionId"]

        # get chat history
        user_id = event_body.get("user_id", "default_user_id")
        
        ddb_history_obj = DynamoDBChatMessageHistory(
            sessions_table_name=sessions_table_name,
            messages_table_name=messages_table_name,
            session_id=session_id,
            user_id=user_id,
            client_type=client_type,
        )
        # print(chat_session_table,session_id,DynamoDBChatMessageHistory)
        # chat_history = ddb_history_obj.messages_as_langchain

        event_body["chat_history"] = ""
        event_body["ws_connection_id"] = ws_connection_id
        event_body["session_id"] = session_id
        event_body["debug_level"] = debug_level
        event_body['stream'] = stream 
        event_body['custom_message_id'] = custom_message_id
        event_body['question'] = question

        main_entry_start = time.time()
        contexts = []

        # choose entry to execute
        biz_type = event_body.get("type", Type.COMMON)
        entry_executor = get_entry(biz_type)
        response:dict = entry_executor(event_body)

        answer = response["answer"]
        sources = ""
        contexts = ""
        debug_info = ""
        rag_config = response["rag_config"]

        main_entry_end = time.time()
        main_entry_elpase = main_entry_end - main_entry_start
        # logger.info(
        #     f"{custom_message_id} running time of main entry {entry_type} : {main_entry_elpase}s"
        # )

        response_kwargs = dict(
            stream=stream,
            session_id=event_body["session_id"],
            ws_connection_id=event_body["ws_connection_id"],
            entry_type=entry_type,
            question=question,
            request_timestamp=request_timestamp,
            answer=answer,
            sources=sources,
            get_contexts=get_contexts,
            contexts=contexts,
            enable_debug=enable_debug,
            debug_info=debug_info,
            ws_client=ws_client,
            ddb_history_obj="",
            message_id = str(uuid.uuid4()),
            client_type=client_type,
            custom_message_id=custom_message_id,
            main_entry_end=main_entry_end,
            rag_config=rag_config,
        )
        r = process_response(**response_kwargs)
    if not stream:
        return r
    return {"statusCode": 200, "body": "All records have been processed"}(f"event:{event}")
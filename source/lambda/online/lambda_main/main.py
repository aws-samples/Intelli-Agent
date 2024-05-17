import json
import os
import logging
import time
import uuid

import boto3
# print(boto3.__version__)
import sys

from common_utils.ddb_utils import DynamoDBChatMessageHistory
from lambda_main.main_utils.online_entries import get_entry
from lambda_main.main_utils.response_utils import process_response
from common_utils.constant import EntryType
from common_utils.logger_utils import get_logger
from common_utils.websocket_utils import load_ws_client
from common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper

logger = get_logger("main")
# region = os.environ["AWS_REGION"]
# embedding_endpoint = os.environ.get("embedding_endpoint", "")
# aos_index = os.environ.get("aos_index", "")

sessions_table_name = os.environ.get("sessions_table_name", "")
messages_table_name = os.environ.get("messages_table_name", "")
websocket_url = os.environ.get("websocket_url", "")


# class APIException(Exception):
#     def __init__(self, message, code: str = None):
#         if code:
#             super().__init__("[{}] {}".format(code, message))
#         else:
#             super().__init__(message)

# def handle_error(func):
#     """Decorator for exception handling"""

#     def wrapper(*args, **kwargs):
#         try:
#             return func(*args, **kwargs)
#         except APIException as e:
#             # logger.exception(e)
#             raise e
#         except Exception as e:
#             # logger.exception(e)
#             raise RuntimeError(
#                 "Unknown exception, please check Lambda log for more details"
#             )

#     return wrapper

# @handle_error
@chatbot_lambda_call_wrapper
def lambda_handler(event_body:dict, context:dict):
    # messages = event_body.get("messages", [])
    # query = event_body['query']
    stream = context['stream']
    request_timestamp = context['request_timestamp']
    ws_connection_id = context.get('ws_connection_id')
    if stream:
        load_ws_client(websocket_url)

    client_type = event_body.get("client_type", "default_client_type")
    entry_type = event_body.get("entry_type", EntryType.COMMON).lower()
    session_id = event_body.get("session_id", None)
    custom_message_id = event_body.get("custom_message_id", "")
    user_id = event_body.get("user_id", "default_user_id")

    if not session_id:
        session_id = f"session_{int(request_timestamp)}"
    
    ddb_history_obj = DynamoDBChatMessageHistory(
            sessions_table_name=sessions_table_name,
            messages_table_name=messages_table_name,
            session_id=session_id,
            user_id=user_id,
            client_type=client_type,
        )
    
    # print(chat_session_table,session_id,DynamoDBChatMessageHistory)
    chat_history = ddb_history_obj.messages_as_langchain

    logger.info(f'chat_history:\n{json.dumps(chat_history,ensure_ascii=False,indent=2)}')

    event_body['stream'] = stream 
    event_body["chat_history"] = chat_history
    event_body["ws_connection_id"] = ws_connection_id
    event_body['custom_message_id'] = custom_message_id
    event_body['ddb_history_obj'] = ddb_history_obj
    event_body['request_timestamp'] = request_timestamp
    event_body['message_id'] = str(uuid.uuid4())
    entry_executor = get_entry(entry_type)
    response:dict = entry_executor(event_body)

    # response_kwargs = dict(
    #         stream=stream,
    #         session_id=event_body["session_id"],
    #         ws_connection_id=event_body["ws_connection_id"],
    #         entry_type=entry_type,
    #         question=query,
    #         request_timestamp=request_timestamp,
    #         answer=answer,
    #         sources=sources,
    #         get_contexts=get_contexts,
    #         contexts=contexts,
    #         enable_debug=enable_debug,
    #         debug_info=debug_info,
    #         ws_client=ws_client,
    #         ddb_history_obj="",
    #         message_id = str(uuid.uuid4()),
    #         client_type=client_type,
    #         custom_message_id=custom_message_id,
    #         main_entry_end=main_entry_end,
    #         rag_config=rag_config,
    #     )
    r = process_response(event_body,response)
    if not stream:
        return r
    return "All records have been processed"
    # return {"statusCode": 200, "body": "All records have been processed"}(f"event:{event}")





    # request_timestamp = time.time()
    # logger.info(f"request_timestamp :{request_timestamp}")
    # logger.info(f"event:{event}")
    # logger.info(f"context:{context}")

    # if "Records" not in event:
    #     # Restful API invocation
    #     # event["Records"] = [{"body": json.dumps(event)}]
    #     event["Records"] = [event]

    # for event_body in event["Records"]:
        # record_event = json.loads(record["body"])
        # Get request body
        # event_body = json.loads(record_event["body"])
        # model = event_body['model']
        # session_id = event_body.get("session_id", None) or "N/A"
        # messages = event_body.get("messages", [])
        # deal with stream parameter
        # stream = _is_websocket_request(record_event)
        # stream = False
        # if stream:
        #     load_ws_client()

        # logger.info(f"stream decode: {stream}")
        # client_type = event_body.get("client_type", "default_client_type")
        # entry_type = event_body.get("type", EntryType.COMMON).lower()
        # enable_debug = event_body.get("enable_debug", False)
        # get_contexts = event_body.get("get_contexts", False)
        # session_id = event_body.get("session_id", None)
        # ws_connection_id = None

        # debug_level = event_body.get("debug_level", logging.INFO)
        # logger.setLevel(debug_level)

        # if messages and entry_type != Type.MARKET_CONVERSATION_SUMMARY.value:
        #     # assert len(messages) == 1
        #     question = messages[-1]["content"]
        #     custom_message_id = messages[-1].get("custom_message_id", "")
        # else:
        #     question = ""  # MARKET_CONVERSATION_SUMMARY
        #     custom_message_id = event.get("custom_message_id", "")

        # question = messages[-1]["content"]
        # custom_message_id = messages[-1].get("custom_message_id", "")
        
        # custom_message_id 字段位置不合理
        # _, question = process_input_messages(messages)
        # role = "user"

        # if not session_id:
        #     session_id = f"session_{int(request_timestamp)}"

        # if stream:
        #     ws_connection_id = record_event["requestContext"]["connectionId"]

        # get chat history
        # user_id = event_body.get("user_id", "default_user_id")
        
        # ddb_history_obj = DynamoDBChatMessageHistory(
        #     sessions_table_name=sessions_table_name,
        #     messages_table_name=messages_table_name,
        #     session_id=session_id,
        #     user_id=user_id,
        #     client_type=client_type,
        # )
        # print(chat_session_table,session_id,DynamoDBChatMessageHistory)
        # chat_history = ddb_history_obj.messages_as_langchain

    #     event_body["chat_history"] = chat_history
    #     event_body["ws_connection_id"] = ws_connection_id
    #     event_body["session_id"] = session_id
    #     event_body["debug_level"] = debug_level
    #     event_body['stream'] = stream 
    #     event_body['custom_message_id'] = custom_message_id
    #     event_body['question'] = question

    #     main_entry_start = time.time()
    #     contexts = []

    #     # choose entry to execute
    #     biz_type = event_body.get("type", EntryType.COMMON)
    #     entry_executor = get_entry(biz_type)
    #     response:dict = entry_executor(event_body)

    #     answer = response["answer"]
    #     sources = ""
    #     contexts = ""
    #     debug_info = ""
    #     rag_config = response["rag_config"]

    #     main_entry_end = time.time()
    #     main_entry_elpase = main_entry_end - main_entry_start
    #     # logger.info(
    #     #     f"{custom_message_id} running time of main entry {entry_type} : {main_entry_elpase}s"
    #     # )

    #     response_kwargs = dict(
    #         stream=stream,
    #         session_id=event_body["session_id"],
    #         ws_connection_id=event_body["ws_connection_id"],
    #         entry_type=entry_type,
    #         question=question,
    #         request_timestamp=request_timestamp,
    #         answer=answer,
    #         sources=sources,
    #         get_contexts=get_contexts,
    #         contexts=contexts,
    #         enable_debug=enable_debug,
    #         debug_info=debug_info,
    #         ws_client=ws_client,
    #         ddb_history_obj="",
    #         message_id = str(uuid.uuid4()),
    #         client_type=client_type,
    #         custom_message_id=custom_message_id,
    #         main_entry_end=main_entry_end,
    #         rag_config=rag_config,
    #     )
    #     r = process_response(**response_kwargs)
    # if not stream:
    #     return r
    # return {"statusCode": 200, "body": "All records have been processed"}(f"event:{event}")
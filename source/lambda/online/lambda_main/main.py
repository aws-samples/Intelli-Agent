import json
import os
import uuid

from common_utils.ddb_utils import DynamoDBChatMessageHistory
from lambda_main.main_utils.online_entries import get_entry
from lambda_main.main_utils.response_utils import process_response
from common_utils.constant import EntryType
from common_utils.logger_utils import get_logger
from common_utils.websocket_utils import load_ws_client
from common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
from common_utils.serialization_utils import JSONEncoder

logger = get_logger("main")

sessions_table_name = os.environ.get("sessions_table_name", "")
messages_table_name = os.environ.get("messages_table_name", "")
websocket_url = os.environ.get("websocket_url", "")


@chatbot_lambda_call_wrapper
def lambda_handler(event_body:dict, context:dict):
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
    
    chat_history = ddb_history_obj.messages_as_langchain

    # logger.info(f'chat_history:\n{json.dumps(chat_history,ensure_ascii=False,indent=2)}')

    event_body['stream'] = stream 
    event_body["chat_history"] = chat_history
    event_body["ws_connection_id"] = ws_connection_id
    event_body['custom_message_id'] = custom_message_id
    event_body['ddb_history_obj'] = ddb_history_obj
    event_body['request_timestamp'] = request_timestamp
    event_body['message_id'] = str(uuid.uuid4())

    # logger.info(f"event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}")
    entry_executor = get_entry(entry_type)
    response:dict = entry_executor(event_body)

    r = process_response(event_body,response)
    if not stream:
        return r
    return "All records have been processed"
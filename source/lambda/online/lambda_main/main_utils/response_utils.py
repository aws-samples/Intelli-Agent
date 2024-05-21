import copy
import csv
import json
import logging
import os
import time
import traceback
from common_utils.ddb_utils import DynamoDBChatMessageHistory
from common_utils.websocket_utils import send_to_ws_client
from common_utils.constant import StreamMessageType
logger = logging.getLogger("response_utils")

class WebsocketClientError(Exception):
    pass


def write_chat_history_to_ddb(
        query:str,
        answer:str,
        ddb_obj:DynamoDBChatMessageHistory,
        message_id,
        custom_message_id,
        entry_type
        ):
    ddb_obj.add_user_message(
                f"user_{message_id}", custom_message_id, entry_type, query
            )
    ddb_obj.add_ai_message(
        f"ai_{message_id}",
        custom_message_id,
        entry_type,
        answer,
        input_message_id=f"user_{message_id}",
    )



def api_response(event_body:dict,response:dict):
    ddb_history_obj = event_body["ddb_history_obj"]

    answer = response.pop("answer")

    if not isinstance(answer, str):
        answer = json.dumps(answer, ensure_ascii=False)

    write_chat_history_to_ddb(
        query=event_body['query'],
        answer=response['answer'],
        ddb_obj=ddb_history_obj,
        message_id=event_body['message_id'],
        custom_message_id=event_body['custom_message_id'],
        entry_type=event_body['entry_type']
    )

    
    return {
            "session_id": event_body['session_id'],
            # "client_type": eventclient_type,
            # "object": "chat.completion",
            "entry_type": event_body['entry_type'],
            "created": time.time(),
            "total_time": time.time()-event_body["request_timestamp"],
            "message": {
                "role": "assistant",
                "content": answer
            },
            **response
    }


def stream_response(event_body:dict, response:dict):
    request_timestamp = event_body["request_timestamp"]
    entry_type = event_body["entry_type"]
    message_id = event_body["message_id"]
    log_first_token_time = True 
    ws_connection_id = event_body["ws_connection_id"]
    custom_message_id = event_body["custom_message_id"]
    
    answer = response.pop("answer")
    if isinstance(answer, str):
        answer = iter([answer])

    ddb_history_obj = event_body["ddb_history_obj"]

    try:
        send_to_ws_client(message={
                "message_type": StreamMessageType.START,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
            },
            ws_connection_id=ws_connection_id
        )
        answer_str = ""

        filter_sentence_fn = lambda x: x

        for i, chunk in enumerate(answer):
            if i == 0 and log_first_token_time:
                first_token_time = time.time()
                
                logger.info(
                    f"{custom_message_id} running time of first token whole {entry_type} entry: {first_token_time-request_timestamp}s"
                )
            chunk = filter_sentence_fn(chunk)
            send_to_ws_client(message={
                    "message_type": StreamMessageType.CHUNK,
                    "message_id": f"ai_{message_id}",
                    "custom_message_id": custom_message_id,
                    "message": {
                        "role": "assistant",
                        "content": chunk,
                        # "knowledge_sources": sources,
                    },
                    "chunk_id": i,
                },
                ws_connection_id=ws_connection_id
            )

            answer_str += chunk

        if log_first_token_time:
            logger.info(
                f"{custom_message_id} running time of last token whole {entry_type} entry: {time.time()-request_timestamp}s"
            )

        logger.info(f"answer: {answer_str}")

        write_chat_history_to_ddb(
            query=event_body['query'],
            answer=answer_str,
            ddb_obj=ddb_history_obj,
            message_id=message_id,
            custom_message_id=custom_message_id,
            entry_type=entry_type
        )

        # sed source and contexts
        if response:
            context_msg = {
                "message_type": StreamMessageType.CONTEXT,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
                **response
            }
            send_to_ws_client(
                message=context_msg,
                ws_connection_id=ws_connection_id
            )

        # send end
        send_to_ws_client(
            {
                "message_type": StreamMessageType.END,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
            },
            ws_connection_id=ws_connection_id
        )
    except WebsocketClientError:
        error = traceback.format_exc()
        logger.info(error)
        # _stop_stream()
    except:
        # bedrock error
        error = traceback.format_exc()
        logger.info(error)
        send_to_ws_client(
            {
                "message_type": StreamMessageType.ERROR,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
                "message": {"content": error},
            },
            ws_connection_id=ws_connection_id
        )


class WebSocketCallback:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, answer, contexts):
        kwargs = {"answer": answer, "contexts": contexts}
        kwargs.update(**self.kwargs)

        return stream_response(**kwargs)

def process_response(event_body,response):
    stream = event_body["stream"]
    if stream:
        return stream_response(event_body,response)
    return api_response(event_body,response)

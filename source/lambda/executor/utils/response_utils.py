import copy
import json
import logging
import time
import traceback

from .constant import EntryType

logger = logging.getLogger()

class StreamMessageType:
    START = "START"
    END = "END"
    ERROR = "ERROR"
    CHUNK = "CHUNK"
    CONTEXT = "CONTEXT"

class WebsocketClientError(Exception):
    pass

def api_response(**kwargs):
    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    session_id = kwargs["session_id"]
    entry_type = kwargs["entry_type"]
    # model = kwargs["model"]
    request_timestamp = kwargs["request_timestamp"]
    answer = kwargs["answer"]
    sources = kwargs["sources"]
    get_contexts = kwargs["get_contexts"]
    contexts = kwargs["contexts"]
    enable_debug = kwargs["enable_debug"]
    debug_info = kwargs["debug_info"]
    chat_history = kwargs["chat_history"]
    message_id = kwargs["message_id"]
    question = kwargs["question"]

    if not isinstance(answer, str):
        answer = json.dumps(answer, ensure_ascii=False)

    if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
        chat_history.add_user_message(f"user_{message_id}", question, entry_type)
        chat_history.add_ai_message(f"ai_{message_id}", answer, entry_type)

    # 2. return rusult
    llmbot_response = {
        "id": session_id,
        "object": "chat.completion",
        "created": int(request_timestamp),
        # "model": model,
        # "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": answer,
                    "knowledge_sources": sources,
                },
                "message_id": f"ai_{message_id}",
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "entry_type": entry_type,
    }

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }
    if get_contexts:
        llmbot_response["contexts"] = contexts
    if enable_debug:
        debug_info["contexts"] = contexts
        llmbot_response["debug_info"] = debug_info
    response["body"] = json.dumps(llmbot_response)
    response["headers"] = resp_header

    return response


def stream_response(**kwargs):
    session_id = kwargs["session_id"]
    # model = kwargs.["model"]
    request_timestamp = kwargs["request_timestamp"]
    answer = kwargs["answer"]
    sources = kwargs["sources"]
    get_contexts = kwargs["get_contexts"]  # bool
    contexts = kwargs["contexts"]  # retrieve result
    enable_debug = kwargs["enable_debug"]
    debug_info = kwargs["debug_info"]
    ws_client = kwargs["ws_client"]
    chat_history = kwargs["chat_history"]
    message_id = kwargs["message_id"]
    question = kwargs["question"]
    entry_type = kwargs["entry_type"]
    ws_connection_id = kwargs["ws_connection_id"]
    log_first_token_time = kwargs.get('log_first_token_time',True)

    if isinstance(answer, str):
        answer = [answer]

    def _stop_stream():
        pass
        # if not isinstance(answer,list):
        #     answer.close()

    def _send_to_ws_client(message: dict):
        try:
            llmbot_response = {
                "id": session_id,
                "object": "chat.completion",
                "created": int(request_timestamp),
                # "model": '',
                # "usage": {
                #     "prompt_tokens": 13,
                #     "completion_tokens": 7,
                #     "total_tokens": 20,
                # },
                "choices": [message],
                "entry_type": entry_type,
            }
            ws_client.post_to_connection(
                ConnectionId=ws_connection_id,
                Data=json.dumps(llmbot_response).encode("utf-8"),
            )
        except:
            # convert to websocket error
            raise WebsocketClientError

    try:
        _send_to_ws_client(
            {
                "message_type": StreamMessageType.START,
                "message_id": f"ai_{message_id}",
            }
        )
        answer_str = ""
        for i, ans in enumerate(answer):
            if i ==0 and log_first_token_time:
                logger.info(
                    f'execute time until first token generated: {time.time()-request_timestamp}s'
                )

            _send_to_ws_client(
                {
                    "message_type": StreamMessageType.CHUNK,
                    "message_id": f"ai_{message_id}",
                    "message": {
                        "role": "assistant",
                        "content": ans,
                        # "knowledge_sources": sources,
                    },
                    "chunk_id": i,
                }
            )
            answer_str += ans

        # add to chat history ddb table
        if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
            chat_history.add_user_message(f"user_{message_id}", question, entry_type)
            chat_history.add_ai_message(f"ai_{message_id}", answer_str, entry_type)
        # sed source and contexts
        context_msg = {
            "message_type": StreamMessageType.CONTEXT,
            "message_id": f"ai_{message_id}",
            "knowledge_sources": sources,
        }
        if get_contexts:
            context_msg.update({"contexts": contexts})

        if enable_debug:
            debug_info["stream_full_answer"] = answer_str
            context_msg.update({"debug_info": debug_info})

        _send_to_ws_client(context_msg)
        # send end
        _send_to_ws_client(
            {
                "message_type": StreamMessageType.END,
                "message_id": f"ai_{message_id}",
            }
        )
    except WebsocketClientError:
        error = traceback.format_exc()
        logger.info(error)
        _stop_stream()
    except:
        # bedrock error
        error = traceback.format_exc()
        logger.info(error)
        _send_to_ws_client(
            {
                "message_type": StreamMessageType.ERROR,
                "message_id": f"ai_{message_id}",
                "message": {"content": error},
            }
        )


class WebSocketCallback:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, answer, contexts):
        kwargs = {"answer": answer, "contexts": contexts}
        kwargs.update(**self.kwargs)

        return stream_response(**kwargs)


def process_response(**kwargs):
    stream = kwargs["stream"]
    if stream:
        return stream_response(**kwargs)
    return api_response(**kwargs)

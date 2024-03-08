import copy
import csv
import json
import logging
import time
import traceback
from .constant import EntryType

logger = logging.getLogger()

# load sensitive words from local csv file
sensitive_words = set()
with open('sensitive_word.csv', mode='r') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        sensitive_words.add(row[0])

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
    ddb_history_obj = kwargs["ddb_history_obj"]
    message_id = kwargs["message_id"]
    question = kwargs["question"]
    client_type = kwargs["client_type"]
    custom_message_id = kwargs["custom_message_id"]

    if not isinstance(answer, str):
        answer = json.dumps(answer, ensure_ascii=False)

    if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
        ddb_history_obj.add_user_message(
            question, f"user_{message_id}", custom_message_id, entry_type
        )
        ddb_history_obj.add_ai_message(
            answer, f"ai_{message_id}", custom_message_id, entry_type
        )

    # 2. return rusult
    llmbot_response = {
        "session_id": session_id,
        "client_type": client_type,
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
                "custom_message_id": custom_message_id,
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
    ddb_history_obj = kwargs["ddb_history_obj"]
    message_id = kwargs["message_id"]
    question = kwargs["question"]
    entry_type = kwargs["entry_type"]
    ws_connection_id = kwargs["ws_connection_id"]
    log_first_token_time = kwargs.get("log_first_token_time", True)
    client_type = kwargs["client_type"]
    custom_message_id = kwargs["custom_message_id"]
    main_entry_end = kwargs["main_entry_end"]

    if isinstance(answer, str):
        answer = [answer]

    def _stop_stream():
        pass
        # if not isinstance(answer,list):
        #     answer.close()

    def _send_to_ws_client(message: dict):
        try:
            llmbot_response = {
                "session_id": session_id,
                "client_type": client_type,
                "object": "chat.completion",
                "created": int(request_timestamp),
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

    def filter_sensitive_words(sentence):
        for sensitive_word in sensitive_words:
            length = len(sensitive_word)
            sentence = sentence.replace(sensitive_word, '*' * length)
        return sentence

    def rebranding_words(sentence):
        rebranding_dict = {'AWS': 'Amazon Web Services'}
        for key, value in rebranding_dict.items():
            sentence = sentence.replace(key, value)
        return sentence

    try:
        _send_to_ws_client(
            {
                "message_type": StreamMessageType.START,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
            }
        )
        answer_str = ""
        accumulated_chunk_ans = ""
        stop_signals = {',', '.', '?', '!', '，', '。', '！', '？'}
        for i, ans in enumerate(answer):
            if i == 0 and log_first_token_time:
                first_token_time = time.time()
                logger.info(
                    f"{custom_message_id} running time of first token generated {entry_type} : {first_token_time-main_entry_end}s"
                )
                logger.info(
                    f"{custom_message_id} running time of first token whole {entry_type} : {first_token_time-request_timestamp}s"
                )

            # accumulate words to make a sentence that could be filtered by sensitive words and rebranding
            if not (len(ans) > 0 and ans[-1] in stop_signals):
                accumulated_chunk_ans += ans
                continue

            accumulated_chunk_ans += ans

            # filter sensitive words
            filtered_accumulated_chunk_ans = filter_sensitive_words(accumulated_chunk_ans)

            # rebranding
            rebranding_filtered_accumulated_chunk_ans = rebranding_words(filtered_accumulated_chunk_ans)

            _send_to_ws_client(
                {
                    "message_type": StreamMessageType.CHUNK,
                    "message_id": f"ai_{message_id}",
                    "custom_message_id": custom_message_id,
                    "message": {
                        "role": "assistant",
                        "content": rebranding_filtered_accumulated_chunk_ans,
                        # "knowledge_sources": sources,
                    },
                    "chunk_id": i,
                }
            )

            # clean up
            accumulated_chunk_ans = ""

            answer_str += rebranding_filtered_accumulated_chunk_ans

        if log_first_token_time:
            logger.info(
                f"{custom_message_id} running time of last token whole {entry_type} : {time.time()-request_timestamp}s"
            )

        # add to chat history ddb table
        if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
            ddb_history_obj.add_user_message(
                question, f"user_{message_id}", custom_message_id, entry_type
            )
            ddb_history_obj.add_ai_message(
                answer_str, f"ai_{message_id}", custom_message_id, entry_type
            )
        # sed source and contexts
        context_msg = {
            "message_type": StreamMessageType.CONTEXT,
            "message_id": f"ai_{message_id}",
            "custom_message_id": custom_message_id,
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
                "custom_message_id": custom_message_id,
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
                "custom_message_id": custom_message_id,
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

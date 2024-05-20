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
# from utils.constant import EntryType, StreamMessageType
# from .content_filter_utils.content_filters import (
#     MarketContentFilter,
#     token_to_sentence_gen_market,
# )

logger = logging.getLogger("response_utils")

# marketing
# market_content_filter = MarketContentFilter()


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
    # response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    # session_id = kwargs["session_id"]
    # entry_type = kwargs["entry_type"]
    # # model = kwargs["model"]
    # request_timestamp = kwargs["request_timestamp"]
    # answer = kwargs["answer"]
    # sources = kwargs["sources"]
    # get_contexts = kwargs["get_contexts"]
    # contexts = kwargs["contexts"]
    # enable_debug = kwargs["enable_debug"]
    # debug_info = kwargs["debug_info"]
    ddb_history_obj = event_body["ddb_history_obj"]
    # message_id = kwargs["message_id"]
    # question = kwargs["question"]
    # client_type = kwargs["client_type"]
    # custom_message_id = kwargs["custom_message_id"]

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

    # if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
    #     ddb_history_obj.add_user_message(
    #         f"user_{message_id}", custom_message_id, entry_type, question
    #     )
    #     ddb_history_obj.add_ai_message(
    #         f"ai_{message_id}",
    #         custom_message_id,
    #         entry_type,
    #         answer,
    #         input_message_id=f"user_{message_id}",
    #     )

    # 2. return rusult
    # llmbot_response = {
    #     "session_id": session_id,
    #     "client_type": client_type,
    #     "object": "chat.completion",
    #     "created": int(request_timestamp),
    #     # "model": model,
    #     # "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
    #     "choices": [
    #         {
    #             "message": {
    #                 "role": "assistant",
    #                 "content": answer,
    #                 # "knowledge_sources": sources,
    #             },
    #             "message_id": f"ai_{event_body['message_id}",
    #             "custom_message_id": custom_message_id,
    #             "finish_reason": "stop",
    #             "index": 0,
    #         }
    #     ],
    #     "entry_type": entry_type,
    # }

    # resp_header = {
    #     "Content-Type": "application/json",
    #     "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    #     "Access-Control-Allow-Origin": "*",
    #     "Access-Control-Allow-Methods": "*",
    # }
    # if get_contexts:
    #     llmbot_response["contexts"] = contexts
    # if enable_debug:
    #     debug_info["contexts"] = contexts
    #     llmbot_response["debug_info"] = debug_info
    # response["body"] = json.dumps(llmbot_response)
    # response["headers"] = resp_header
    answer = response.pop("answer")
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
    # session_id = kwargs["session_id"]
    # # model = kwargs.["model"]
    request_timestamp = event_body["request_timestamp"]
    # answer = kwargs["answer"]
    entry_type = event_body["entry_type"]
    # sources = kwargs["sources"]
    # get_contexts = kwargs["get_contexts"]  # bool
    # contexts = kwargs["contexts"]  # retrieve result
    # enable_debug = kwargs["enable_debug"]
    # debug_info = kwargs["debug_info"]
    # ws_client = kwargs["ws_client"]
    # ddb_history_obj = kwargs["ddb_history_obj"]
    message_id = event_body["message_id"]
    log_first_token_time = True 
    # question = kwargs["question"]


    ws_connection_id = event_body["ws_connection_id"]
    # log_first_token_time = kwargs.get("log_first_token_time", True)
    # client_type = kwargs["client_type"]
    custom_message_id = event_body["custom_message_id"]
    # main_entry_end = kwargs["main_entry_end"]

    
    answer = response.pop("answer")
    if isinstance(answer, str):
        answer = iter([answer])

    ddb_history_obj = event_body["ddb_history_obj"]

    # def _stop_stream():
    #     pass
    #     # if not isinstance(answer,list):
    #     #     answer.close()

    # def _send_to_ws_client(message: dict):
    #     try:
    #         llmbot_response = {
    #             "session_id": session_id,
    #             "client_type": client_type,
    #             "object": "chat.completion",
    #             "created": int(request_timestamp),
    #             "choices": [message],
    #             "entry_type": entry_type,
    #         }
    #         ws_client.post_to_connection(
    #             ConnectionId=ws_connection_id,
    #             Data=json.dumps(llmbot_response).encode("utf-8"),
    #         )
    #     except:
    #         data_to_send = json.dumps(llmbot_response).encode("utf-8")
    #         logger.info(
    #             f"Send to ws client error occurs, the message to send is: {data_to_send}"
    #         )
    #         # convert to websocket error
    #         raise WebsocketClientError

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
        # if market_content_filter.check_market_entry(entry_type):
        #     answer = token_to_sentence_gen_market(answer)
        #     filter_sentence_fn = market_content_filter.filter_sentence
        #     sources = market_content_filter.filter_source(kwargs["sources"])

        for i, chunk in enumerate(answer):
            if i == 0 and log_first_token_time:
                first_token_time = time.time()
                # logger.info(
                #     f"{custom_message_id} running time of first token generated {entry_type} : {first_token_time-main_entry_end}s"
                # )
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

        # add to chat history ddb table
        # if entry_type != EntryType.MARKET_CONVERSATION_SUMMARY.value:
            # ddb_history_obj.add_user_message(
            #     f"user_{message_id}", custom_message_id, entry_type, question
            # )
            # ddb_history_obj.add_ai_message(
            #     f"ai_{message_id}",
            #     custom_message_id,
            #     entry_type,
            #     answer_str,
            #     input_message_id=f"user_{message_id}",
            # )
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
        # if get_contexts:
        #     context_msg.update({"contexts": contexts})

        # if enable_debug:
        #     debug_info["stream_full_answer"] = answer_str
        #     context_msg.update({"debug_info": debug_info})

        # _send_to_ws_client(context_msg)
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

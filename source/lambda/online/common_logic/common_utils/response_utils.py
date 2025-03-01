import json
import logging
import time
import traceback
from common_logic.common_utils.ddb_utils import DynamoDBChatMessageHistory
from common_logic.common_utils.websocket_utils import check_stop_signal, clear_stop_signal, send_to_ws_client
from common_logic.common_utils.constant import StreamMessageType
from common_logic.common_utils.logger_utils import get_logger
logger = get_logger("response_utils")


class WebsocketClientError(Exception):
    pass


def write_chat_history_to_ddb(
        query: str,
        answer: str,
        ddb_obj: DynamoDBChatMessageHistory,
        message_id,
        custom_message_id,
        entry_type,
        additional_kwargs=None,
):
    ddb_obj.add_user_message(
        f"user_{message_id}", custom_message_id, entry_type, query, additional_kwargs
    )
    ddb_obj.add_ai_message(
        f"ai_{message_id}",
        custom_message_id,
        entry_type,
        answer,
        input_message_id=f"user_{message_id}",
        additional_kwargs=additional_kwargs
    )


def api_response(event_body: dict, response: dict):
    ddb_history_obj = event_body["ddb_history_obj"]
    answer = response["answer"]
    if not isinstance(answer, str):
        answer = json.dumps(answer, ensure_ascii=False)

    write_chat_history_to_ddb(
        query=event_body['query'],
        answer=answer,
        ddb_obj=ddb_history_obj,
        message_id=event_body['message_id'],
        custom_message_id=event_body['custom_message_id'],
        entry_type=event_body['entry_type'],
        additional_kwargs=response.get("ddb_additional_kwargs", {})
    )

    return {
        "session_id": event_body['session_id'],
        "entry_type": event_body['entry_type'],
        "created": time.time(),
        "total_time": time.time()-event_body["request_timestamp"],
        "message": {
            "role": "assistant",
            "content": answer
        },
        **response['extra_response']
    }


def stream_response(event_body: dict, response: dict):
    request_timestamp = event_body["request_timestamp"]
    entry_type = event_body["entry_type"]
    message_id = event_body["message_id"]
    log_first_token_time = True
    ws_connection_id = event_body["ws_connection_id"]
    custom_message_id = event_body["custom_message_id"]
    answer = response["answer"]
    if isinstance(answer, str):
        answer = iter([answer])

    ddb_history_obj = event_body["ddb_history_obj"]
    answer_str = ""

    try:
        send_to_ws_client(message={
            "message_type": StreamMessageType.START,
            "message_id": f"ai_{message_id}",
            "custom_message_id": custom_message_id,
        },
            ws_connection_id=ws_connection_id
        )

        #TODO: check whether answer has reason chunks
        for i, chunk in enumerate(answer):
            # Check for stop signal before sending each chunk
            if check_stop_signal(ws_connection_id):
                logger.info(
                    f"Stop signal detected for connection {ws_connection_id}")
                # Send END message to notify frontend and stop the session
                send_to_ws_client(
                    {
                        "message_type": StreamMessageType.END,
                        "message_id": f"ai_{message_id}",
                        "custom_message_id": custom_message_id
                    },
                    ws_connection_id=ws_connection_id
                )
                clear_stop_signal(ws_connection_id)
                return answer_str

            if i == 0 and log_first_token_time:
                first_token_time = time.time()
                logger.info(
                    f"{custom_message_id} running time of first token whole {entry_type} entry: {first_token_time-request_timestamp}s"
                )

            send_to_ws_client(message={
                "message_type": StreamMessageType.CHUNK,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
                "message": {
                    "role": "assistant",
                    "content": chunk,
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
            entry_type=entry_type,
            additional_kwargs=response.get("ddb_additional_kwargs", {})
        )

        # Send source and contexts
        if response:
            context_msg = {
                "message_type": StreamMessageType.CONTEXT,
                "message_id": f"ai_{message_id}",
                "custom_message_id": custom_message_id,
                "ddb_additional_kwargs": {},
                **response["extra_response"]
            }

            figure = response.get("extra_response").get("ref_figures", [])
            if figure:
                # context_msg["ddb_additional_kwargs"]["figure"] = figure[:2]
                context_msg["ddb_additional_kwargs"]["figure"] = figure

            ref_doc = response.get("extra_response").get("ref_docs", [])
            if ref_doc:
                md_images = []
                md_image_list = []
                for doc in ref_doc:
                    # Look for markdown image pattern in reference doc: ![alt text](image_path)
                    doc_content = doc.get("page_content", "")
                    for line in doc_content.split('\n'):
                        img_start = line.find("![")
                        while img_start != -1:
                            try:
                                alt_end = line.find("](", img_start)
                                img_end = line.find(")", alt_end)

                                if alt_end != -1 and img_end != -1:
                                    image_path = line[alt_end + 2:img_end]
                                    # Remove optional title if present
                                    if '"' in image_path or "'" in image_path:
                                        image_path = image_path.split(
                                            '"')[0].split("'")[0].strip()
                                    if image_path:
                                        have_same_image = False
                                        for md_image_item in md_image_list:
                                            if image_path in md_image_item:
                                                have_same_image = True

                                        md_image_json = {
                                            "content_type": "md_image",
                                            "figure_path": image_path
                                        }
                                        if not have_same_image and md_image_json not in md_images:
                                            md_images.append(md_image_json)
                                            md_image_list.append(image_path)
                                # Look for next image in the same line
                                img_start = line.find("![", img_start + 2)
                            except Exception as e:
                                logger.error(
                                    f"Error processing markdown image: {str(e)}, in line: {line}")
                                # Skip to next image pattern in this line
                                img_start = line.find("![", img_start + 2)
                                continue

                if md_images:
                    context_msg["ddb_additional_kwargs"].setdefault(
                        "figure", []).extend(md_images)

            send_to_ws_client(
                message=context_msg,
                ws_connection_id=ws_connection_id
            )

        # Send END message
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
        clear_stop_signal(ws_connection_id)
    except:
        # Bedrock error
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
        clear_stop_signal(ws_connection_id)
    return answer_str


class WebSocketCallback:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, answer, contexts):
        kwargs = {"answer": answer, "contexts": contexts}
        kwargs.update(**self.kwargs)

        return stream_response(**kwargs)


def process_response(event_body, response):
    stream = event_body.get("stream", True)
    if stream:
        return stream_response(event_body, response)

    return api_response(event_body, response)

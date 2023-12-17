import time 
import json 
import logging 
import traceback

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
    session_id = kwargs['session_id']
    model = kwargs['model']
    request_timestamp = kwargs['request_timestamp']
    answer = kwargs['answer']
    sources = kwargs['sources']
    get_contexts = kwargs['get_contexts']
    contexts = kwargs['contexts']
    enable_debug = kwargs['enable_debug']
    debug_info = kwargs['debug_info']
    
    # 2. return rusult
    llmbot_response = {
        "id": session_id,
        "object": "chat.completion",
        "created": int(request_timestamp),
        "model": model,
        "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": answer,
                    "knowledge_sources": sources,
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
    }

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    if get_contexts:
        llmbot_response["contexts"] = contexts
    if enable_debug:
        llmbot_response["debug_info"] = debug_info
    response["body"] = json.dumps(llmbot_response)
    response["headers"] = resp_header

    return response

def stream_response(**kwargs):
    session_id = kwargs['session_id']
    model = kwargs['model']
    request_timestamp = kwargs['request_timestamp']
    answer = kwargs['answer']
    sources = kwargs['sources']
    get_contexts = kwargs['get_contexts'] # bool
    contexts = kwargs['contexts']  # retrieve result
    enable_debug = kwargs['enable_debug']
    debug_info = kwargs['debug_info']
    ws_client = kwargs['ws_client']
    
    if isinstance(answer,str):
        answer = [answer]

    def _stop_stream():
        if not isinstance(answer,list):
            answer.close()
    
    def _send_to_ws_client(message:dict):
        try:
            llmbot_response = {
                "id": session_id,
                "object": "chat.completion",
                "created": int(request_timestamp),
                "model": model,
                "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
                "choices": [
                    message
                ]
            }
            ws_client.post_to_connection(
                ConnectionId=session_id,
                Data=json.dumps(llmbot_response).encode('utf-8')
            )
        except:
            # convert to websocket error
            raise WebsocketClientError
    
    try:
        _send_to_ws_client({
                "message_type": StreamMessageType.START,
            })
        answer_str = ""
        for i,ans in enumerate(answer):
            _send_to_ws_client({
                        "message_type": StreamMessageType.CHUNK,
                        "message": {
                            "role": "assistant",
                            "content": ans,
                            # "knowledge_sources": sources,
                        },
                        "chunck_id": i,
                    })
            answer_str += ans
        # sed source and contexts
        context_msg = {
             "message_type": StreamMessageType.CONTEXT,
             "knowledge_sources": sources,
            }
        if get_contexts:
            context_msg.update({"contexts":contexts})
        
        if enable_debug:
            debug_info['knowledge_qa_llm']['answer'] = answer_str
            context_msg.update({"debug_info":debug_info})
        
        _send_to_ws_client(context_msg)
        # send end
        _send_to_ws_client({
                "message_type": StreamMessageType.END,
        })
    except WebsocketClientError:
        error = traceback.format_exc()
        logger.info(error)
        _stop_stream()
    except:
        # bedrock error
        error = traceback.format_exc()
        logger.info(error)
        _send_to_ws_client({
             "message_type": StreamMessageType.ERROR,
             "message": {'content':error}
        })

def process_response(**kwargs):
    stream = kwargs['stream']
    if stream:
        return stream_response(**kwargs)
    return api_response(**kwargs)

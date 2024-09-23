import os
import sys
import time

try:
    from websocket import create_connection
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install websocket-client")
    from websocket import create_connection

import json

# ws_url from api gateway
jwt = "aaa"
# ws_url = f"wss://w2druwcuc3.execute-api.us-west-2.amazonaws.com/prod/?idToken={jwt}"
ws_url = f"wss://j2vt20lsri.execute-api.us-west-2.amazonaws.com/prod?idToken={jwt}"

sample_questions = {
    "general_qa": {
        "query": "客服电话是多少？",
        "entry_type": "common",
        "session_id": f"test_{time.time()}",
        "chatbot_config": {
            "goods_id": "",
            "chatbot_mode": "agent",
            "use_history": True,
            "enable_trace": True,
            "use_websearch": False,
            "google_api_key": "",
            "default_index_config": {"rag_index_ids": ["Admin"]},
            "default_llm_config": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "endpoint_name": "",
                "model_kwargs": {"temperature": 0.01, "max_tokens": 1000},
            },
            "agent_config": {"only_use_rag_tool": True},
        },
    },
    "item_qa": {
        "query": "有类似的吗？",
        "entry_type": "common",
        "session_id": f"test_{time.time()}",
        "chatbot_config": {
            "goods_id": "50d59a7a-738a-4c84-9b9e-2fd119f8aacd",
            "chatbot_mode": "agent",
            "use_history": True,
            "enable_trace": True,
            "use_websearch": False,
            "google_api_key": "",
            "default_index_config": {"rag_index_ids": ["Admin"]},
            "default_llm_config": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "endpoint_name": "",
                "model_kwargs": {"temperature": 0.01, "max_tokens": 1000},
            },
            "agent_config": {"only_use_rag_tool": True},
        },
    },
    "item_comparison": {
        "query": "这两个商品哪个好？",
        "entry_type": "common",
        "session_id": f"test_{time.time()}",
        "chatbot_config": {
            "goods_id": "50d59a7a-738a-4c84-9b9e-2fd119f8aacd, f4d6df27-394b-42bb-b1e3-130eca6feef6",
            "chatbot_mode": "agent",
            "use_history": True,
            "enable_trace": True,
            "use_websearch": False,
            "google_api_key": "",
            "default_index_config": {"rag_index_ids": ["Admin"]},
            "default_llm_config": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "endpoint_name": "",
                "model_kwargs": {"temperature": 0.01, "max_tokens": 1000},
            },
            "agent_config": {"only_use_rag_tool": True},
        },
    },
}


def get_answer(body, ws):
    ws.send(json.dumps(body))
    start_time = time.time()
    answer = ""
    while True:
        ret = json.loads(ws.recv())
        message_type = ret["message_type"]
        # print('message_type',message_type)
        if message_type == "START":
            pass
        elif message_type == "CHUNK":
            print(ret["message"]["content"], end="", flush=True)
        elif message_type == "END":
            break
        elif message_type == "ERROR":
            print(ret["message"]["content"])
            break
        elif message_type == "MONITOR":
            print("monitor info: ", ret["message"])
    return answer


if __name__ == "__main__":
    # test_multi_turns()
    ws = create_connection(ws_url)
    body = sample_questions["general_qa"]
    r = get_answer(body, ws)
    ws.close()

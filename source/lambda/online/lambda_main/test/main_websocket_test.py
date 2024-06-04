import os 
import sys
import time
import time
import dotenv 
dotenv.load_dotenv()
try:
    from websocket import create_connection
except ModuleNotFoundError:
    os.system(f'{sys.executable} -m pip install websocket-client')
    from websocket import create_connection
import json 

# ws_url from api gateway
jwt = os.environ['jwt']
ws_url = f"wss://luwo6r87ub.execute-api.us-west-2.amazonaws.com/prod/?idToken={jwt}"

def get_answer(body,ws):
    ws.send(json.dumps(body))
    start_time = time.time()
    answer = ""
    while True:
        ret = json.loads(ws.recv())
        message_type = ret['message_type']
        # print('message_type',message_type)
        if message_type == "START":
            pass
        elif message_type == "CHUNK":
            print(ret['message']['content'],end="",flush=True)
        elif message_type == "END":
            break
        elif message_type == "ERROR":
            print(ret['message']['content'])
            break
        elif message_type == "MONITOR":
            print("monitor info: ",ret['message'])
    return answer

def test():
    ws = create_connection(ws_url)
    body = {
        "query": "hi",
        "entry_type": "common",
        "session_id":f"test_{time.time()}",
        "chatbot_config": {
            "chatbot_mode": "chat",
            "use_history": True,
            "use_websearch": False,
            "default_llm_config":{
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0", 
                "model_kwargs": {"temperature": 0.0, "max_tokens": 4096}
            }
        }
    }
    r = get_answer(body,ws)
    ws.close()  
    return r  


def test_multi_turns():
    session_id = time.time()
    ws = create_connection(ws_url)
    body = {
        "query": "今天星期几",
        "entry_type": "common",
        "session_id":f"test_{session_id}",
        "chatbot_config": {
            "chatbot_mode": "rag",
            "use_history": True,
            "use_websearch": False,
            "default_llm_config":{
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0", 
                "model_kwargs": {"temperature": 0.0, "max_tokens": 4096}
            }
        }
    }
    r = get_answer(body,ws)
    ws.close() 

    print()

    ws = create_connection(ws_url)
    body = {
        "query": "我在北京",
        "entry_type": "common",
        "session_id":f"test_{session_id}",
        "chatbot_config": {
            "chatbot_mode": "rag",
            "use_history": True,
            "use_websearch": False,
            "default_llm_config":{
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0", 
                "model_kwargs": {"temperature": 0.0, "max_tokens": 4096}
            }
        }
    }
    r = get_answer(body,ws)
    ws.close() 

if __name__ == "__main__":
    test_multi_turns()



    
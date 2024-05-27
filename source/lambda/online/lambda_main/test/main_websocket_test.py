import os 
import sys
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
ws_url = f"wss://owvlrxmqfi.execute-api.us-west-2.amazonaws.com/prod/?idToken={jwt}"

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
    ws = create_connection(
        ws_url
    )
    import time

    body = {
        "query": "hi",
        "entry_type": "common",
        "session_id":f"test_{time.time()}",
        "chatbot_config": {
            "intention_config":{
                "retrievers": [
                        {
                            "type": "qq",
                            "workspace_ids": ["yb_intent"],
                            "config": {
                                "top_k": 10,
                            }
                        },
                    ]
            },
            "query_process_config":{
                "conversation_query_rewrite_config":{
                    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
                    }
                    },
            "agent_config":{
                "model_id":"anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs": {"temperature":0.0,"max_tokens":4096},
                "tools":[{"name":"give_final_response"},{"name":"search_lihoyo"}]
        },
        "chat_config":{
            "model_id":"anthropic.claude-3-sonnet-20240229-v1:0"
        }  
        }
    }
    r = get_answer(body,ws)
    ws.close()  
    return r  


if __name__ == "__main__":
    test()



    
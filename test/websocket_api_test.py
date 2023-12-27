import os 
import sys
try:
    from websocket import create_connection
except ModuleNotFoundError:
    os.system(f'{sys.executable} -m pip install websocket-client')
    from websocket import create_connection
import json 

# find ws_url from api gateway
ws_url = "wss://omjou492fe.execute-api.us-west-2.amazonaws.com/prod/"

ws = create_connection(ws_url)

body = {
    "action": "sendMessage",
    "model": "knowledge_qa",
    "messages": [{"role": "user","content": "要在Amazon EC2控制台中创建一个EBS卷快照,需要采取哪些步骤?"}],
    "temperature": 0.7,
    "type" : "market_chain", 
    "enable_q_q_match": True,
    "enable_debug": False,
    "llm_model_id":'anthropic.claude-v2'
}
ws.send(json.dumps(body))

while True:
    ret = json.loads(ws.recv())
    message_type = ret['choices'][0]['message_type']
    if message_type == "START":
        continue 
    elif message_type == "CHUNK":
        print(ret['choices'][0]['message']['content'],end="",flush=True)
    elif message_type == "END":
        break
    elif message_type == "ERROR":
        print(ret['choices'][0]['message']['content'])
        break 
    elif message_type == "CONTEXT":
        print('sources: ',ret['choices'][0]['knowledge_sources'])

ws.close()  
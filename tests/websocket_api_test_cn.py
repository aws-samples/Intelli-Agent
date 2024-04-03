import os 
import sys
import time
try:
    from websocket import create_connection
except ModuleNotFoundError:
    os.system(f'{sys.executable} -m pip install websocket-client')
    from websocket import create_connection
import json 
from dotenv import load_dotenv
load_dotenv()

# find ws_url from api gateway
ws_url = os.getenv('WS_URL')
ws = create_connection(ws_url)

question_library = [
    "IoT Core是否支持Qos2？",
    "在API Gateway REST API中，能否将JSON数据作为GET方法的请求体发送？",
    "Lambda Authorizer 上下文响应是否有大小限制？如果存在，限制是多少？",
    "Lambda Docker镜像的最大支持多少？"
    # "IoT Core是否支持Qos2？",
    # "如何在Amazon Forecast上导出已经训练好的模型，以便在其他地方部署？",
    "如何将Kinesis Data Streams配置为AWS Lambda的事件源？",
    "要在Amazon EC2控制台中创建一个EBS卷快照,需要采取哪些步骤?",
    "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?"
]

endpoint_name = 'instruct-internlm2-chat-7b-f7dc2'
model_id = "internlm2-chat-7b"

body = {
    # "action": "sendMessage",
    "model": "knowledge_qa",
    # "messages": [{"role": "user","content": question_library[-1]}],
    # "messages": [{"role": "user","content": question_library[-1]}],
    "messages": [{"role": "user","content": '什么是Bedrock？'}],
    "temperature": 0.7,
    "type" : "market_chain", 
    "get_contexts" : True,
    "retriever_config":{
            "retriever_top_k": 20,
            "chunk_num": 2,
            "using_whole_doc": False,
            "reranker_top_k": 10,
            "enable_reranker": True
            },
    "generator_llm_config":{
        "model_kwargs":{
            "max_new_tokens": 2000,
            "temperature": 0.1,
            "top_p": 0.9
        },
        "model_id": model_id,
        "endpoint_name": endpoint_name,
        "context_num": 1
    },
    "query_process_config":{
        "conversation_query_rewrite_config":{
            "model_id":model_id,
            "endpoint_name":endpoint_name
        },
        "translate_config":{
            "model_id":model_id,
            "endpoint_name": endpoint_name
        }
    },
    "intent_config":{ 
        "model_id": model_id,
        "endpoint_name": endpoint_name
    }
}
    # "session_id":f"test_{int(time.time())}"


# body.update({"retriever_top_k": 1,
#             "chunk_num": 2,
#             "using_whole_doc": False,
#             "reranker_top_k": 10,
#             "enable_reranker": True})


ws.send(json.dumps(body))
start_time = time.time()
while True:
    ret = json.loads(ws.recv())
    try:
        message_type = ret['choices'][0]['message_type']
    except:
        print(ret)
        print(f'total time: {time.time()-start_time}' )
        raise
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
        print()
        print('contexts',ret)
        # print('sources: ',ret['choices'][0]['knowledge_sources'])

ws.close()  
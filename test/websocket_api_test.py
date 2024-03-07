import os 
import sys
import time
try:
    from websocket import create_connection
except ModuleNotFoundError:
    os.system(f'{sys.executable} -m pip install websocket-client')
    from websocket import create_connection
import json 

# find ws_url from api gateway
# ws_url = "wss://omjou492fe.execute-api.us-west-2.amazonaws.com/prod/"
ws_url = "wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/prod/"
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

body = {
    "action": "sendMessage",
    "model": "knowledge_qa",
    # "messages": [{"role": "user","content": question_library[-1]}],
    # "messages": [{"role": "user","content": question_library[-1]}],
    "messages": [{"role": "user","content": '什么是Bedrock？', "custom_message_id": f"test_dashboard_{time.time()}"}],
    "temperature": 0.7,
    "type" : "market_chain", 
    "retriever_config":{
        "using_whole_doc": False,
        "chunk_num": 2,
    },
    # "enable_q_q_match": True,
    # "enable_debug": False,
    # "llm_model_id":'anthropic.claude-v2:1',
    "get_contexts":True,
    "generator_llm_config":{
        "model_kwargs":{
            "max_new_tokens": 1000,
            "temperature": 0.01,
            "top_p": 0.9,
            "timeout":120
        },
        "llm_model_id": "internlm2-chat-7b",
        # "endpoint_name": "instruct-internlm2-chat-7b-f7dc2",
        "llm_model_endpoint_name": "internlm2-chat-20b-4bits-2024-03-04-06-32-53-653",#"baichuan2-13b-chat-4bits-2024-01-28-15-46-43-013",
        "context_num": 1
    },
    "model_kwargs":{
        "max_new_tokens": 1000,
        "temperature": 0.01,
        "top_p": 0.9,
        "timeout":120
    },
    "llm_model_id": "internlm2-chat-20b",
    # "endpoint_name": "instruct-internlm2-chat-7b-f7dc2",
    "llm_model_endpoint_name": "internlm2-chat-20b-4bits-2024-03-04-06-32-53-653",#"baichuan2-13b-chat-4bits-2024-01-28-15-46-43-013",
    "context_num": 1,
    "custom_message_id": f"test_dashboard_{int(time.time())}"
    # "session_id":f"test_{int(time.time())}"
}


body.update({"retriever_top_k": 1,
            "chunk_num": 2,
            "using_whole_doc": False,
            "reranker_top_k": 10,
            "reranker_type": "no_reranker"})


# body = {
#     "session_id":"325e217e-5023-4fbc-ace9-fb053c3188a5",
#     "type":"market_conversation_summary"
# }

# body = {
#     "action": "sendMessage",
#     "session_id": "869272a2-493d-4908-b088-fd7cb033bf5e",
#     "model": "knowledge_qa",
#     "messages": [
#         {
#             "role": "user",
#             "content": "Lambda冷启动怎么解决？"
#         }
#     ],
#     "type": "market_chain",
#     "temperature": 0.1
# }

# body = {
#     "action": "sendMessage",
#     "model": "chat",
#     "messages": [{"role": "user","content": "今天天气怎么样"}],
#     "temperature": 0.7,
#     "type" : "market_chain", 
#     # "enable_q_q_match": True,
#     # "enable_debug": False,
#     "llm_model_id":'anthropic.claude-v2:1',
#     "get_contexts":True,
#     # "session_id":f"test_{int(time.time())}"
# }
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
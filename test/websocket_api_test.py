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
ws_url = "wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/prod/"


def get_answer(body):
    ws.send(json.dumps(body))
    start_time = time.time()
    answer = ""
    context = None
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
            answer += ret['choices'][0]['message']['content']
            print(ret['choices'][0]['message']['content'],end="",flush=True)
        elif message_type == "END":
            break
        elif message_type == "ERROR":
            print(ret['choices'][0]['message']['content'])
            break 
        elif message_type == "CONTEXT":
            print()
            context=ret
            print('contexts',ret)
            # print('sources: ',ret['choices'][0]['knowledge_sources'])

    ws.close()  
    return answer,context

# ws_url = "wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/v1"
# wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/prod/

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

<<<<<<< Updated upstream
market_test_cases = [
    'EC2',
    "LAMBDA",
    '亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？',
    'Amazon Lambda的免费套餐包含什么？',
    '在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？',
    'Amazon Lambda函数是什么？',
    '日志通是什么？',
    'lambda是什么？',
    '2024北京国际车展上，亚马逊云科技会参加吗？',
    '3月份在深圳有生成式AI的活动吗？',
    '2024年会举办出海全球化论坛吗？',
    '2024年出海全球化论坛的会议日程是什么？',
    '2024亚马逊云科技出海全球化论坛什么时候举办？',
    '请问怎么关闭账号？',
    '个人能否注册账号？',
    '怎么开发票？',
    '使用CDN服务要备案吗？',
    '今天是几月几号？',
    '亚马逊云科技有上海区域吗？',
    '我上一个问题是什么？',
    '如何注册AWS账号?',
    '如何注册亚马逊云科技账号',
    '怎么申请免费试用？',
    '怎么试用服务器？',
    '无法连接服务器',
    '连接不上服务器',
    '账号被停用了怎么解决',
    '备案流程',
    '怎么备案',
    '人工服务',
    '为什么产生了费用？不是免费试用吗？',
    '申请退款',
    '服务器报价/服务器多少钱？'
]


# endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
# model_id = "internlm2-chat-20b"
entry_type = "market_chain"
# workspace_ids = ["aos_index_mkt_faq_qq","aos_index_acts_qd"]


# body = {
#     "get_contexts": True,
#     "model": "knowledge_qa",
#     # "messages": [{"role": "user","content": question_library[-1]}],
#     # "messages": [{"role": "user","content": question_library[-1]}],
#     "messages": [{"role": "user","content": '什么是Bedrock？', "custom_message_id": f"test_dashboard_{time.time()}"}],
#     # "temperature": 0.7,
#     "type" : "market_chain", 
#     "retriever_config":{
#         "using_whole_doc": False,
#         "chunk_num": 2,
#     },
#     # "enable_q_q_match": True,
#     # "enable_debug": False,
#     # "llm_model_id":'anthropic.claude-v2:1',
#     "get_contexts":True,
#     "generator_llm_config":{
#         "model_kwargs":{
#             "max_new_tokens": 1000,
#             "temperature": 0.01,
#             "top_p": 0.9,
#             "timeout":120
#         },
#         "llm_model_id": "internlm2-chat-7b",
#         # "endpoint_name": "instruct-internlm2-chat-7b-f7dc2",
#         "llm_model_endpoint_name": "internlm2-chat-20b-4bits-2024-03-04-06-32-53-653",#"baichuan2-13b-chat-4bits-2024-01-28-15-46-43-013",
#         "context_num": 1
#     },
#     "model_kwargs":{
#         "max_new_tokens": 1000,
#         "temperature": 0.01,
#         "top_p": 0.9,
#         "timeout":120
#     },
#     "llm_model_id": "internlm2-chat-20b",
#     # "endpoint_name": "instruct-internlm2-chat-7b-f7dc2",
#     "llm_model_endpoint_name": "internlm2-chat-20b-4bits-2024-03-04-06-32-53-653",#"baichuan2-13b-chat-4bits-2024-01-28-15-46-43-013",
#     "context_num": 1,
#     "custom_message_id": f"test_dashboard_{int(time.time())}"
#     # "session_id":f"test_{int(time.time())}"
# }


# body.update({"retriever_top_k": 1,
#             "chunk_num": 2,
#             "using_whole_doc": False,
#             "reranker_top_k": 10,
#             "reranker_type": "no_reranker"})
=======
body = {
    "action": "sendMessage",
    "model": "knowledge_qa",
    # "messages": [{"role": "user","content": question_library[-1]}],
    # "messages": [{"role": "user","content": question_library[-1]}],
    "messages": [{"role": "user","content": '2024北京国际车展上，亚马逊云科技会参加吗？', "custom_message_id": f"test_dashboard_{time.time()}"}],
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
>>>>>>> Stashed changes


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
for question in market_test_cases:
    ws = create_connection(ws_url)
    print('-*'*50)
    print(f'question: ', question)
    body = {
        "get_contexts": False,
        "type" : entry_type, 
        "messages": [{"role": "user","content": question}]
    }
    get_answer(body)
    
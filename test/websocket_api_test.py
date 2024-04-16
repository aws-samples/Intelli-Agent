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
            message = ret['choices'][0]
            context = context or ""
            if "_chunk_data" in message:
                context += message.pop('_chunk_data')
                if message["chunk_id"] + 1 != message['total_chunk_num']:
                    continue
                # print('context chunk num',message['total_chunk_num'])
                message.update(json.loads(context))
                context = message
            print()
            context=ret
            print('contexts',message)
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

# market_test_cases = [
#     'EC2',
#     "LAMBDA",
#     '亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？',
#     'Amazon Lambda的免费套餐包含什么？',
#     '在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？',
#     'Amazon Lambda函数是什么？',
#     '日志通是什么？',
#     'lambda是什么？',
#     '2024北京国际车展上，亚马逊云科技会参加吗？',
#     '3月份在深圳有生成式AI的活动吗？',
#     '2024年会举办出海全球化论坛吗？',
#     '2024年出海全球化论坛的会议日程是什么？',
#     '2024亚马逊云科技出海全球化论坛什么时候举办？',
#     '请问怎么关闭账号？',
#     '个人能否注册账号？',
#     '怎么开发票？',
#     '使用CDN服务要备案吗？',
#     '今天是几月几号？',
#     '亚马逊云科技有上海区域吗？',
#     '我上一个问题是什么？',
#     '如何注册AWS账号?',
#     '如何注册亚马逊云科技账号',
#     '怎么申请免费试用？',
#     '怎么试用服务器？',
#     '无法连接服务器',
#     '连接不上服务器',
#     '账号被停用了怎么解决',
#     '备案流程',
#     '怎么备案',
#     '人工服务',
#     '为什么产生了费用？不是免费试用吗？',
#     '申请退款',
#     '服务器报价/服务器多少钱？'
# ]

market_test_cases = [
    "亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？",
    "Amazon Lambda的免费套餐包含什么？",
    "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
    "Amazon Lambda函数是什么？",
    "日志通是什么？",
    "lambda是什么？",
    "Claude 3是什么？",
    "如何在EMR中实现跨可用区的高可用？",
    "你能分享一些AWS客户在机器学习CI/CD方面的成功故事吗？",
    "在S3的分段上传中，是否可以将每个部分的大小限制在5MB以下？",
    "2024北京国际车展上，亚马逊云科技会参加吗？",
    "3月份在深圳有生成式AI的活动吗？",
    "2024年会举办出海全球化论坛吗？",
    "2024年出海全球化论坛的会议日程是什么？",
    "2024亚马逊云科技出海全球化论坛什么时候举办？",
    "请问怎么关闭账号？",
    "个人能否注册账号？",
    "怎么开发票？",
    "使用CDN服务要备案吗？",
    "今天是几月几号？",
    "亚马逊云科技有上海区域吗？",
    "我上一个问题是什么？",
    "如何快速搭建一个网站？",
    "客服联系时间",
    "客服工作时间？",
    "谢谢"
]

# market_test_cases = ['将计算资源与Lambda函数部署在相同AZ是否会降低延迟？']
# market_test_cases = ['Claude 3 Opus的最大令牌数是多少？']
# market_test_cases = ['我想在Cognito控制台为用户池添加 Lambda 触发器，应该如何操作？']
# 请回答关于亚马逊云科技/aws/amazon的问题:
# market_test_cases = ['我们项目在调研比较简单一点的大数据环境，你们这个好像挺麻烦的，Airflow是一个单独的产品，Kafka也是一个单独的产品。如果有类似阿里云的DataWorks这样的产品就很好。请问我们有类似阿里dataworks的solution吗？']
market_test_cases = ['亚马逊存在种族歧视吗？']

entry_type = "market_chain"
# entry_type = "dgr"

for question in market_test_cases:
    ws = create_connection(ws_url)
    print('-*'*50)
    print(f'question: ', question)
    body = {
        "get_contexts": True,
        "response_config": {
            # context return with chunk
            "context_return_with_chunk": True
        },
        "type" : entry_type, 
        "messages": [{"role": "user","content": question}],
    }
    # body = {
    #     "retriever_config": {
    #         "qd_config": {
    #             "context_num": 2,
    #             "using_whole_doc": False,
    #         }
    #     },
    #     "get_contexts": True,
    #     "response_config": {
    #         # context return with chunk
    #         "context_return_with_chunk": True
    #     },
    #     "type" : entry_type, 
    #     "messages": [{"role": "user","content": question}],
    #     "generator_llm_config": {"context_num":4}
    # }
    get_answer(body)
    
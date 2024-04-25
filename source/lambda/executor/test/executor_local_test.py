import json
import sys
import csv
import os 
import time 
import uuid

from dotenv import load_dotenv
# load_dotenv(
#     dotenv_path=os.path.join(os.path.dirname(__file__),'.env_global_430')
# )

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__),'.env_global')
)

import logging
log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# sys.path.append("llm-bot/source/lambda/executor/utils")
sys.path.append("../executor")
# sys.path.append("utils")
# sys.path.append(".")
# import aos_utils
# from requests_aws4auth import AWS4Auth
# import boto3
# region = "us-east-1"
# credentials = boto3.Session().get_credentials()
# aos_utils.awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

# import os
# region = os.environ["AWS_REGION"]
# print(region)
import main
import os
from collections import defaultdict
from utils.ddb_utils import DynamoDBChatMessageHistory

contexts = defaultdict(str)

class DummyWebSocket:
    def post_to_connection(self,ConnectionId,Data):
        data = json.loads(Data)
        ret = data
        message_type = ret['choices'][0]['message_type']
        if message_type == "START":
            pass
        elif message_type == "CHUNK":
            print(ret['choices'][0]['message']['content'],end="",flush=True)
        elif message_type == "END":
            return 
        elif message_type == "ERROR":
            print(ret['choices'][0]['message']['content'])
            return 
        elif message_type == "CONTEXT":
            # print(ret['choices'][0])
            message:dict = ret['choices'][0]
            if "_chunk_data" in ret['choices'][0]:
                contexts[message['message_id']] += message['_chunk_data']
                if message["chunk_id"] + 1 != message['total_chunk_num']:
                    return 
                _chunk_data = contexts.pop(message['message_id'])
                print('context chunk num',message['total_chunk_num'])
                message.update(json.loads(_chunk_data))
            
            print('knowledge_sources',message['knowledge_sources'])
            print('response msg',message['response_msg'])
            print('trace_infos',message['trace_infos'])


            # if ret['choices'][0].get('contexts'):
            #     print('contexts num',len(ret['choices'][0].get('contexts')))
            #     print('contexts avg len: ', sum(len(i) for i in ret['choices'][0]['contexts'])/len(ret['choices'][0]['contexts']))
                # print('sources: ',ret['choices'][0]['contexts'])

main.ws_client = DummyWebSocket()

def generate_answer(query=None,
                    messages=None,
                    # temperature=0.7,
                    enable_debug=True,
                    retrieval_only=False,
                    type="market_chain",
                    model="knowledge_qa",
                    stream=False,
                    retriever_index="test-index",
                    session_id=None,
                    rag_parameters=None
                    ):
    rag_parameters = rag_parameters or {}

    if query:
        messages = [
                {
                    "role": "user",
                    "content": query
                }
            ]
    else:
        assert messages and isinstance(messages,list), messages

    body = {
            "messages": messages,
            # "temperature": temperature,
            # "enable_debug": enable_debug,
            # "retrieval_only": retrieval_only,
            # "retriever_index": retriever_index,
            "type": type,
            "model": model,
            "session_id":session_id,
            "enable_debug":True,
            }
    body.update(rag_parameters)
    event = {
        "body": json.dumps(body)
    }
    if stream:
        event["requestContext"] = {
            "eventType":"MESSAGE",
            "connectionId":f'test_{int(time.time())}'
        }

    context = None
    response = main.lambda_handler(event, context)
    if response is None:
        return
    if not stream:
        body = json.loads(response["body"])
        answer = body["choices"][0]["message"]["content"]
        knowledge_sources = body["choices"][0]["message"]["knowledge_sources"]
        debug_info = body["debug_info"]
        return (answer,
                knowledge_sources,
                debug_info)

def retrieval(query, temperature=0.7, enable_q_q_match=False, enable_debug=True, retrieval_only=True):
    event = {
        "body": json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "aos_faq_index": "chatbot-index-9",
                "aos_ug_index": "chatbot-index-1",
                "model": "knowledge_qa",
                "temperature": temperature,
                "enable_q_q_match": enable_q_q_match,
                "enable_debug": enable_debug,
                "retrieval_only": retrieval_only, 
                # "type": "dgr"
            }
        )
    }
    context = None
    response = main.lambda_handler(event, context)
    body = json.loads(response["body"])
    knowledges = body["knowledges"]
    debug_info = body["debug_info"]
    return (knowledges, debug_info)

def retrieval_test(top_k = 20):
    error_log = open("error.log", "w")
    debug_log = open("debug.log", "w")
    with open('test/techbot-qa-test-3.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["URL"] == "repost-qa-csdc/20230915" or row["URL"].startswith("https://repost"):
                continue
            query = row["TechBot Question"]
            docs, debug_info = retrieval(query)
            source_list = []
            for doc in docs[:top_k]:
                source_list.append(doc["metadata"]["source"].lower())
            # gt_answer = row['Answer'].replace('\n', ' ')
            correct_url = row['URL'].split('#')[0].lower()
            correct_url_2 = correct_url.replace("zh_cn/", "")
            correct_url_3 = correct_url.replace("userguide/", "windowsguide/")
            if correct_url not in source_list and correct_url_2 not in source_list and correct_url_3 not in source_list:
                logger.info(f"ERROR QUERY:{query} URL: {source_list} CORRECT URL: {correct_url}")
                error_log.write(f"{query}\t{source_list}\t{correct_url}\n")
            else:
                logger.info(f"CORRECT QUERY:{query} URL: {source_list} CORRECT URL: {correct_url}")
            debug_log.write(f"{query}\n{json.dumps(debug_info, indent=4, ensure_ascii=False)}\n")
    error_log.close()

def eval():
    result_file = open("result.json", "w")
    debug_info_file = open("debug.json", "w")
    result_list = []
    debug_info_list = []
    with open('test/techbot-qa-test-3.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            answer, source, debug_info = generate_answer(row["TechBot Question"])[:3]
            answer = answer.replace('\n', ' ')
            result = {
                "question": row['TechBot Question'],
                "answer": answer,
                "source": source
            }
            if len(row["URL"]) == 32:
                correct_url = "dgr-oncall"
            else:
                correct_url = row['URL'].split('#')[0]
                correct_url_2 = correct_url.replace("zh_cn/", "")
            if correct_url not in source and correct_url_2 not in source:
                logger.info(f"ERROR URL: {source} CORRECT URL: {correct_url}")
            result_list.append(result)
            debug_info_list.append(debug_info)
    json.dump(result_list, result_file, ensure_ascii=False)
    json.dump(debug_info_list, debug_info_file, ensure_ascii=False)


def multiturn_chat_test():
    session_id = f'test_{int(time.time())}'
    generate_answer(
        "《七里香》的演唱者是谁？",
        model='chat',
        stream=True,
        session_id=session_id
        )
    generate_answer(
        "他还有其他什么歌曲",
        model='chat',
        stream=True,
        session_id=session_id
        )
    
    generate_answer(
        "请总结前面的对话。",
        model='chat',
        stream=True,
        session_id=session_id
        )
    
def multiturn_strict_qq_test():
    session_id = f'test_{int(time.time())}'
    generate_answer(
        "IoT Core是否支持Qos2？", 
        model='strict_q_q',
        stream=True,
        session_id=session_id
        )
    generate_answer(
        "IoT Core是否支持Qos2？", 
        model='strict_q_q',
        stream=True,
        session_id=session_id
        )

def qq_match_test():
    r = generate_answer(
        "IoT Core是否支持Qos2？", 
        # model="auto", 
        model="strict_q_q", 
        stream=True,
        type="market_chain", 
    )

def knowledge_qa_test():
    r = generate_answer(
        "什么是Amazon Bedrock", 
        model="knowledge_qa", 
        stream=True,
        type="market_chain", 
    )
    r = generate_answer(
        "如何将Kinesis Data Streams配置为AWS Lambda的事件源？", 
        model="knowledge_qa", 
        stream=True,
        type="market_chain", 
    )
    # print(r[0])
    r = generate_answer(
        "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", 
        model="knowledge_qa", 
        stream=False,
        type="market_chain", 
    )
    print(r[0])
    generate_answer(
        "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", 
        model="knowledge_qa", 
        stream=True,
        type="market_chain", 
    )
    generate_answer(
        "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", 
        model="knowledge_qa", 
        stream=True,
        type="market_chain", 
    )

def test_baichuan_model():
    session_id=f'test_{time.time()}'
    endpoint_name = 'baichuan2-13b-chat-4bits-2024-02-01-03-58-29-048'
    generate_answer(
        "《夜曲》是谁演唱的？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=dict(
            generator_llm_config={
                    "model_kwargs":{
                        "max_new_tokens": 2000,
                        "temperature": 0.1,
                        "top_p": 0.9
                    },
                    "model_id": "Baichuan2-13B-Chat-4bits",
                    "endpoint_name": endpoint_name,
                    "context_num": 2
        })
    )
    generate_answer(
        "他还有哪些其他歌曲？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=dict(
            generator_llm_config={
                    "model_kwargs":{
                        "max_new_tokens": 2000,
                        "temperature": 0.1,
                        "top_p": 0.9
                    },
                    "model_id": "Baichuan2-13B-Chat-4bits",
                    "endpoint_name": endpoint_name,
                    "context_num": 2
        })
    )

    r = generate_answer(
        "解释一下“温故而知新”", 
        model="chat", 
        type="market_chain", 
        stream=False,
        rag_parameters=dict(
            generator_llm_config={
                    "model_kwargs":{
                        "max_new_tokens": 2000,
                        "temperature": 0.1,
                        "top_p": 0.9
                    },
                    "model_id": "Baichuan2-13B-Chat-4bits",
                    "endpoint_name": endpoint_name,
                    "context_num": 2
        })
    )
    print(r[0])

    generate_answer(
        "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", 
        model="knowledge_qa", 
        type="market_chain", 
        stream=True,
        rag_parameters=dict(
            generator_llm_config={
                    "model_kwargs":{
                        "max_new_tokens": 2000,
                        "temperature": 0.1,
                        "top_p": 0.9
                    },
                    "model_id": "Baichuan2-13B-Chat-4bits",
                    "endpoint_name": endpoint_name,
                    "context_num": 1
        })
    )

def test_internlm_model():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"

    endpoint_name = 'internlm2-chat-20b-4bits-2024-02-29-05-37-42-885'
    model_id = "internlm2-chat-20b"

    rag_parameters = {
        "get_contexts":True,
         "retriever_config":{
            "retriever_top_k": 1,
                "chunk_num": 2,
                "using_whole_doc": True,
                "reranker_top_k": 10,
                "enable_reranker": True
        },
        "query_process_config":{
            "conversation_query_rewrite_config":{
                "model_id":model_id,
                "endpoint_name":endpoint_name
            },
            "translate_config":{
                "model_id":model_id,
                "endpoint_name": endpoint_name
            },
            "stepback_config":{
                "model_id":model_id,
                "endpoint_name": endpoint_name
            }
        },
        "intent_config": {
            "model_id": model_id,
            "endpoint_name": endpoint_name
        },
        "generator_llm_config":{
            "model_kwargs":{
                "max_new_tokens": 2000,
                "temperature": 0.1,
                "top_p": 0.9,
                # 'repetition_penalty':1.1
            },
            "model_id": model_id,
            "endpoint_name": endpoint_name,
            "context_num": 1
        }
    }
    
    qq_match_test()
    generate_answer(
        "AWS支持上海region吗？", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    # print(sfg)
    generate_answer(
        "介绍一下Amazon EC2", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    # print(xfg)
    generate_answer(
        "什么是Amazon bedrock？", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )

    generate_answer(
        "《夜曲》是谁演唱的？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    generate_answer(
        "他还有哪些其他歌曲？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )

    r = generate_answer(
        "解释一下“温故而知新”", 
        model="auto", 
        type="market_chain", 
        stream=False,
        rag_parameters=rag_parameters
    )
    print(r[0])


def test_internlm_model_mkt():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    model_id = "internlm2-chat-20b"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name

    rag_parameters = {
        "get_contexts":True,
    }
    
    qq_match_test()
    generate_answer(
        "AWS支持上海region吗？", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    # print(sfg)
    generate_answer(
        "介绍一下Amazon EC2", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    # print(xfg)
    generate_answer(
        "什么是Amazon bedrock？", 
        model="auto", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )

    generate_answer(
        "《夜曲》是谁演唱的？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )
    generate_answer(
        "他还有哪些其他歌曲？", 
        session_id=session_id,
        model="chat", 
        type="market_chain", 
        stream=True,
        rag_parameters=rag_parameters
    )

    r = generate_answer(
        "解释一下“温故而知新”", 
        model="auto", 
        type="market_chain", 
        stream=False,
        rag_parameters=rag_parameters
    )
    print(r[0])



def test_internlm_model_mkt_knowledge_entry_qq_match():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    model_id = "internlm2-chat-20b"
    entry_type = "market_chain_knowledge"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name
    # workspace_ids = ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3"]
    
    questions = [
        "能否通过JDBC连接到RDS for PostgreSQL？ 有相关的指导吗？",
        "如何解决切换RI后网速变慢？",
        "如何升级EC2配置不改变IP",
        "如何/怎么关停账号",
        "请问怎么关闭账号？",
        "个人能否注册账号？",
        "怎么开具发票？",
        "怎么开发票？",
        "使用CDN服务要备案吗？"
    ]
    for question in questions:
        generate_answer(
           question, 
            model="knowledge_qa", 
            type=entry_type, 
            stream=True,
            rag_parameters={
            "get_contexts":True,
            "retriever_config":{
                # "qq_config": {
                #     "qq_match_threshold": 0.8,
                # },
                # "qd_config":{
                #     "qd_match_threshold": 2,
                # # "using_whole_doc": True
                # },
                # "workspace_ids": workspace_ids
            }
            }
        )


def test_internlm_model_mkt_knowledge_entry():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    # endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    endpoint_name = 'internlm2-chat-20b-4bits-continuous-bat-2024-03-23-16-25-28-881'
    # endpoint_name = 'instruct-internlm2-chat-20b-7bae8'
    model_id = "internlm2-chat-20b"
    entry_type = "market_chain"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name
    # workspace_ids = ["aos_index_mkt_faq_qq","aos_index_acts_qd"]
    # workspace_ids = ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3"]
    
    rag_parameters={
        "get_contexts":True,
        "session_id":session_id,
        "response_config": {
            # context return with chunk
            "context_return_with_chunk": True
        },
        "generator_llm_config": {
            "context_num": 1,
        } 
    }

    #  "亚马逊云科技中国区域免费套餐有什么优惠？",
    #   "介绍Amazon Lambda是什么？"
    # messages = [
    #     {
    #     "role":"user",
    #     "content": "请问怎么租用jetson agx orin"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "您好,这是英伟达的产品"
    #     },
    #     {
    #     "role":"user",
    #     "content": "是的,可以租借一台吗"
    #     }
    # ]
    # messages = [
    #     {
    #     "role":"user",
    #     "content": "你好"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "您好"
    #     },
    #     {
    #     "role":"user",
    #     "content": "我是大连阿尔派电子有限公司\n想要了解云服务器的租赁服务"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "中国还是海外的？"
    #     },
    #     {
    #     "role":"user",
    #     "content": "这是需求\n[图片]\n中国\n请联络下销售代表，让他联络我\n电话：13504110365\n邮箱：dw-sun@alpine-china.com\n我需要产品介绍电子版和相应的价格说明\n您有看么"
    #     },
    # ]
    # messages = [
    #     {
    #     "role":"user",
    #     "content": "你好\n我已经选好EC2配置，如何下单？"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "您的account ID提供一下"
    #     },
    #     {
    #     "role":"user",
    #     "content": "654654383149\n78027124@qq.com"
    #     }
    # ]
    # messages = [
    #     {
    #     "role":"user",
    #     "content": "是用于广播，例如紧急撤离\n有的"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "哦哦了解\n您说的离线使用\n是指什么呀\n不用互联网吗"
    #     },
    #     {
    #     "role":"user",
    #     "content": "是的"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "还是下载到本地"
    #     },
    #     {
    #     "role":"user",
    #     "content": "私有化部署"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "用户可以将生成的语音文件下载到本地，然后在云中或本地的应用程序或设备上进行离线播放\n私有化部署不支持 哦"
    #     },
    #     {
    #     "role":"user",
    #     "content": "那是否支持定制音色"
    #     },
    # ]
    # messages = [
        # {
        # "role":"user",
        # "content": "是用于广播，例如紧急撤离\n有的"
        # },
        # {
        # "role":"ai",
        # "content": "哦哦了解\n您说的离线使用\n是指什么呀\n不用互联网吗"
        # },
        # {
        # "role":"user",
        # "content": "是的"
        # },
        # {
        # "role":"ai",
        # "content": "还是下载到本地"
        # },
        # {
        # "role":"user",
        # "content": "私有化部署"
        # },
        # {
        # "role":"ai",
        # "content": "用户可以将生成的语音文件下载到本地，然后在云中或本地的应用程序或设备上进行离线播放\n私有化部署不支持 哦"
        # },
    #     {
    #     "role":"user",
    #     "content": "Claude 3 Opus 模型 预计什么时候上线呀"
    #     },
    # ]

    r = generate_answer(
        "CVM 服务器和 EC2 的区别是什么？",
        # "Amazon Lambda函数是什么？",
        # "Claude 3 Opus 模型 预计什么时候上线呀",
        # "claude 3 opus 模型 预计什么时候上线呀",
        # "您好，我的云服务器的密码忘了则么找回，有什么方法吗",
        # "今天是几月几号？",
        # messages=messages,
        type=entry_type, 
        stream=True,
        rag_parameters=rag_parameters
    )
    # r = generate_answer(
    #     "它和EC2哪个更好？",
    #     type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )
    # r = generate_answer(
    #     "哪个更好？",
    #     type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )

    print(dfg)


    r = generate_answer(
        # "我是按照真实信息填写，不是虚假注册",
        # "你们不了解你们平台的规则吗",
        # "亚马逊云代理商所分发的账号，代理商可以随意删除吗",
        "上一个问题是什么？",
        # "谢谢客服",
        # "请问怎么租用jetson agx orin",
        # "阿里云你了解吗？",
        # "今天星期几？",
        # "您好",
        # "你是谁？",
        # "Amazon Lambda函数是什么？",
        # "GenAI相关活动",
        # "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
        # "什么是amazon ec2?",
        # "亚马逊存在种族歧视吗？",
        # "ec2的全称是什么",
        # "s3在张家港区域有吗",
        # "s3在成都区域有吗？",
        # "2024北京国际车展上，亚马逊云科技会参加吗？",
        # "amazon sagemaker",
        # "近期市场活动推荐？",
        # "好的谢谢", 
        # "Claude 3 Opus的最大令牌数是多少？",
        # "亚马逊云科技有上海区域吗？",
        # "AWS支持上海region吗？", 
        # "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
        # "日志通是什么？",
        # '请介绍下亚马逊云科技IAM',
        # "请介绍下AWS IAM",
        # "亚马逊云科技有上海区域吗？",
        # "亚马逊云科技有上海区域吗?",
        # "客服联系时间",
        # "请问怎么关闭账号？", 
        # "个人能否注册账号？",
        # "3月份在深圳有生成式AI的活动吗？",
        # "2024北京国际车展上，亚马逊云科技会参加吗？",
        # "你能分享一些AWS客户在机器学习CI/CD方面的成功故事吗？",
        # "请问亚马逊云科技中国区域的S3和EC2的价格",
        # "2024亚马逊云科技出海全球化论坛什么时候举办？",
        # "lambda是什么？",
        # "2024年出海全球化论坛的会议日程是什么？",
        # "亚马逊云科技有上海区域吗？",
        # "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
        # "亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？",
        # "什么是日志通",
        # "日志通是什么？",
            # model="knowledge_qa", 
            type=entry_type, 
            stream=True,
            rag_parameters=rag_parameters
    )

    print(r[0])

    print(sfg)

    # generate_answer(
    #     "2024亚马逊云科技出海全球化论坛什么时候举办？",
    #     # "lambda是什么？",
    #     # "2024年出海全球化论坛的会议日程是什么？",
    #     # "亚马逊云科技有上海区域吗？",
    #     # "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
    #         # "亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？",
    #         # "什么是日志通",
    #         # "日志通是什么？",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )
    # for _ in range(10):
    #     generate_answer(
    #         # "2024亚马逊云科技出海全球化论坛什么时候举办？",
    #         # "lambda是什么？",
    #         # "2024年出海全球化论坛的会议日程是什么？",
    #         "亚马逊云科技有上海区域吗？",
    #         # "在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？",
    #             # "亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？",
    #             # "什么是日志通",
    #             # "日志通是什么？",
    #             # model="knowledge_qa", 
    #             type=entry_type, 
    #             stream=True,
    #             rag_parameters=rag_parameters
    #     )


    # print(sfgdfhb)

    # r = generate_answer(
    #         # "lambda",
    #         "什么是日志通",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=False,
    #         rag_parameters=rag_parameters
    # )
    # print(r[0])

    # pritn(sfg)


    # generate_answer(
    #         "火山引擎和阿里云比较",
    #         # "什么是日志通",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )

    # print(fbdfb)

    # generate_answer(
    #         "如何快速搭建一个网站？",
    #         # "什么是日志通",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )
    # generate_answer(
    #         "客户联系时间",
    #         # "什么是日志通",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )
    # generate_answer(
    #         "客户工作时间",
    #         # "什么是日志通",
    #         # model="knowledge_qa", 
    #         type=entry_type, 
    #         stream=True,
    #         rag_parameters=rag_parameters
    # )
 
    # print(sgf)
    
    # 1-26
    # market_test_cases = [
    # 'EC2',
    # "LAMBDA",
    # '亚马逊云科技中国区域免费套餐有哪几种不同类型的优惠？',
    # 'Amazon Lambda的免费套餐包含什么？',
    # '在亚马逊云科技网站上，完成所有账户注册步骤后，什么时候才可以开始使用？',
    # 'Amazon Lambda函数是什么？',
    # '日志通是什么？',
    # 'lambda是什么？',
    # '2024北京国际车展上，亚马逊云科技会参加吗？',
    # '3月份在深圳有生成式AI的活动吗？',
    # '2024年会举办出海全球化论坛吗？',
    # '2024年出海全球化论坛的会议日程是什么？',
    # '2024亚马逊云科技出海全球化论坛什么时候举办？',
    # '请问怎么关闭账号？',
    # '个人能否注册账号？',
    # '怎么开发票？',
    # '使用CDN服务要备案吗？',
    # '今天是几月几号？',
    # '亚马逊云科技有上海区域吗？',
    # '我上一个问题是什么？',
    # '如何注册AWS账号?',
    # '如何注册亚马逊云科技账号',
    # '怎么申请免费试用？',
    # '怎么试用服务器？',
    # '无法连接服务器',
    # '连接不上服务器',
    # '账号被停用了怎么解决',
    # '备案流程',
    # '怎么备案',
    # '人工服务',
    # '为什么产生了费用？不是免费试用吗？',
    # '申请退款',
    # '服务器报价/服务器多少钱？'
    # ]
    
    # 27-44
    market_test_cases = [
        "你是谁？",
        "亚马逊存在种族歧视吗？",
        "ec2的全称是什么",
        "s3在张家港区域有吗",
        "s3在成都区域有吗？",
        "2024北京国际车展上，亚马逊云科技会参加吗？",
        "amazon sagemaker",
        "CVM 服务器和 EC2 的区别是什么？",  # insufficient context / knowledge_qa
        "如何快速搭建一个网站？", #  insufficient context / knowledge_qa
        "2024 峰会什么时候？", # insufficient context / market_event
        "近期市场活动推荐？", # insufficient context / market_event
        "培训资料在哪找？", # insufficient context / knowledge_qa
        "如何参加培训与认证？", # insufficient context / knowledge_qa
        "summit 什么时候开始？", # insufficient context / market_event
        "c5.2xlarge 实例有centos 7.9 AMI吗", # insufficient context / knowledge_qa
        "可以在AWS上租用A100的GPU，跑grok-1的大模型吗", # insufficient context / knowledge_qa
        "阿里云你了解吗？", # normal / knowledge_qa
        "怎么注册企业账号", # insufficient context / knowledge_qa
        "EC2 价格 ？", # insufficient context / knowledge_qa
        "ec2价格是多少 ？", # normal / knowledge_qa
        "redis怎么通过外网链接呢", # insufficient context / knowledge_qa
        "目前的AI模型有能生成辅助K12课堂教学相关图片或视频的方案吗", #  insufficient context / knowledge_qa
        "网站使用了cloudfront 服务，出现html和json类型的文件无法缓存的问题", # insufficient context / knowledge_qa
        "GenAI相关活动", # insufficient context / market_event
        "请介绍下AWS EC2的可用机型" # insufficient context / knowledge_qa
    ]
    ret = []
    for question in market_test_cases:
        r = generate_answer(
            question,
            # "什么是日志通",
            # model="knowledge_qa", 
            type=entry_type, 
            stream=False,
            rag_parameters=rag_parameters
        )
        if r:
            ret.append((question,r[0]))

    for q,a in ret:
        print('*-'*50)
        print(f'Q: {q}\nA: {a}')




# /efs/projects/aws-samples-llm-bot-dev/source/lambda/executor/test/conversation_test_data.json



def test_internlm_model_mkt_knowledge_entry_with_conversation_batch():
    path = "/efs/projects/aws-samples-llm-bot-dev/source/lambda/executor/test/conversation_test_data.json"
    
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    # endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    endpoint_name = 'internlm2-chat-20b-4bits-continuous-bat-2024-03-23-16-25-28-881'
    model_id = "internlm2-chat-20b"
    entry_type = "market_chain"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name
    sessions_table_name = os.environ.get("sessions_table_name", "")
    messages_table_name = os.environ.get("messages_table_name", "")
    custom_message_id = ""
    # workspace_ids = ["aos_index_mkt_faq_qq","aos_index_acts_qd"]
    # workspace_ids = ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3"]
    
    data = json.load(open(path,'r'))
    print("data len: ",len(data))
    import random
    random.Random(42).shuffle(data)
    for datum in data[:200]:
        print('*'*50,flush=True)
        messages = datum['messages']
        session_id=f'test_{time.time()}'
        rag_parameters={
            "get_contexts":True,
            "session_id":session_id,
            "response_config": {
                # context return with chunk
                "context_return_with_chunk": True
            },
            "generator_llm_config": {
                "context_num": 1,
            },
            
        }

        conversation_strs = ["<conversation>"]

        for message in messages:
            conversation_strs.append(f"{message['role']}: {message['content']}")
        
        conversation_strs.append('</conversation>')

        print("\n".join(conversation_strs),flush=True)

        ### 对话标签
        # <conversation>

        # </conversation>
        ##
        ## <answer></answer>


        # 注入历史消息到ddb
        ddb_history_obj = DynamoDBChatMessageHistory(
                sessions_table_name=sessions_table_name,
                messages_table_name=messages_table_name,
                session_id=session_id,
                user_id="default_user_id",
                client_type="default_client_type",
        )
        for message in messages[:-1]:
            message_id = str(uuid.uuid4())
            if message['role'] == "user":
                ddb_history_obj.add_user_message(
                    message_id = message_id,
                    custom_message_id=custom_message_id,
                    entry_type=entry_type,
                    message_content=message['content']
                )
            elif message['role'] == "ai":
                ddb_history_obj.add_ai_message(
                    message_id=message_id,
                    custom_message_id=custom_message_id,
                    entry_type=entry_type,
                    message_content=message['content'],
                    input_message_id=f"user_{message_id}"
                )
            else:
                raise f"invalid role: {message['role']}"
        
        r = generate_answer(
            # "日志通是什么？", 
            messages[-1]['content'], 
            # model="knowledge_qa", 
            type=entry_type, 
            stream=False,
            rag_parameters=rag_parameters
        )
        print(f"<answer>\n{r[0]}\n</answer>",flush=True)
        print('*'*50,flush=True)
        

def test_internlm_model_mkt_knowledge_entry_with_conversation():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    # endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    endpoint_name = 'internlm2-chat-20b-4bits-continuous-bat-2024-03-23-16-25-28-881'
    model_id = "internlm2-chat-20b"
    entry_type = "market_chain"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name
    sessions_table_name = os.environ.get("sessions_table_name", "")
    messages_table_name = os.environ.get("messages_table_name", "")
    custom_message_id = ""
    # workspace_ids = ["aos_index_mkt_faq_qq","aos_index_acts_qd"]
    # workspace_ids = ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3"]
    
    rag_parameters={
        "get_contexts":True,
        "session_id":session_id,
        "response_config": {
            # context return with chunk
            "context_return_with_chunk": True
        },
        "generator_llm_config": {
            "context_num": 1,
        },
        
    }


    messages = [
        {
        "role":"user",
        "content": "请问怎么租用jetson agx orin"
        },
        {
        "role":"ai",
        "content": "您好,这是英伟达的产品"
        },
        {
        "role":"user",
        "content": "是的,可以租借一台吗"
        }
    ]

    # messages = [
    #     {
    #     "role":"user",
    #     "content": "AWS 机器学习平台是什么？"
    #     },
    #     {
    #     "role":"ai",
    #     "content": "sagemaker"
    #     },
    #     {
    #     "role":"user",
    #     "content": "它的优点是什么？"
    #     }
    # ]

    # 注入历史消息到ddb
    ddb_history_obj = DynamoDBChatMessageHistory(
            sessions_table_name=sessions_table_name,
            messages_table_name=messages_table_name,
            session_id=session_id,
            user_id="default_user_id",
            client_type="default_client_type",
    )
    for message in messages[:-1]:
        message_id = str(uuid.uuid4())
        if message['role'] == "user":
            ddb_history_obj.add_user_message(
                message_id = message_id,
                custom_message_id=custom_message_id,
                entry_type=entry_type,
                message_content=message['content']
            )
        elif message['role'] == "ai":
            ddb_history_obj.add_ai_message(
                message_id=message_id,
                custom_message_id=custom_message_id,
                entry_type=entry_type,
                message_content=message['content'],
                input_message_id=f"user_{message_id}"
            )
        else:
            raise f"invalid role: {message['role']}"
    
    generate_answer(
        # "日志通是什么？", 
        messages[-1]['content'], 
        # model="knowledge_qa", 
        type=entry_type, 
        stream=True,
        rag_parameters=rag_parameters
    )



def test_internlm_model_mkt_knowledge_entry_langgraph():
    session_id=f'test_{time.time()}'
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"
    endpoint_name = 'internlm2-chat-20b-4bits-continuous-bat-2024-03-23-16-25-28-881'
    model_id = "internlm2-chat-20b"
    entry_type = "market_chain_knowledge_langgraph"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name

    rag_parameters={
        "get_contexts":True,
        # "session_id":session_id,
        # "retriever_config":{}
    }

    generate_answer(
        # "日志通是什么？", 
        "AWS支持上海region吗？", 
        # model="knowledge_qa", 
        type=entry_type, 
        stream=True,
        rag_parameters=rag_parameters
    )

    print(sfg)

    generate_answer(
        "日志通是什么？", 
        model="knowledge_qa", 
        type=entry_type, 
        stream=True,
        rag_parameters={
            "session_id":session_id,
            "get_contexts":True,
            "retriever_config":{
                "qq_config": {
                    "q_q_match_threshold": 0.9,
                },
                "qd_config":{
                    "qd_match_threshold": 2,
                    "using_whole_doc": True
                },
                "workspace_ids": ["aos_index_mkt_faq_qq","aos_index_acts_qd"]
        }
        }
    )

    generate_answer(
        "AWS支持上海region吗？", 
        model="knowledge_qa", 
        type=entry_type, 
        stream=True,
        rag_parameters={
            "session_id":session_id,
            "get_contexts":True,
            "retriever_config":{
                "qq_config": {
                    "q_q_match_threshold": 0.9,
                },
                "qd_config":{
                    "qd_match_threshold": 2,
                    "using_whole_doc": True
                },
                "workspace_ids": ["aos_index_mkt_faq_qq","aos_index_acts_qd"]
        }
        }
    )


def market_summary_test():
    session_id = f'test_{int(time.time())}'
    generate_answer(
        "lambda 减少冷启动的方法",
        model='knowledge_qa',
        stream=True,
        session_id=session_id
        )
    generate_answer(
        "请介绍一下bedrock",
        model='knowledge_qa',
        stream=True,
        session_id=session_id
        )
    
    generate_answer(
        "今天几号",
        model='chat',
        stream=True,
        session_id=session_id
        )
 
    generate_answer(
        "",
        model='chat',
        stream=True,
        session_id=session_id,
        type='market_conversation_summary'
        )

def market_summary_test2():
    messages = [
            {
                "role": "user",
                "content": "lambda 减少冷启动的方法"
            },
            {
                 "role": "ai",
                 "content": " 好的,这里有几个减少AWS Lambda函数冷启动时间的建议:\n\n1. 优化代码和依赖项。只加载实际需要的代码和库,避免不必要的初始化。使用较新的运行时版本,它们启动更快。\n\n2. 增加函数的内存。更多的内存意味着更多的CPU被分配,这可以加速初始化过程。\n\n3. 启用预置并发和预热。这将确保总是有热启动容器可用。\n\n4. 将不经常更改的初始化逻辑移到层中。层在冷启动之间重用,可以跳过一些初始化工作。\n\n5. 使用容器重用。这将重用最近使用的容器而不是完全冷启动。\n\n6. 跟踪和分析冷启动时间以查找瓶颈。使用工具如 AWS X-Ray 来识别需要优化的地方。\n\n7. 减少函数的复杂性和依赖关系。简单快速的函数冷启动更快。\n\n8. 将不经常更改的资源预置在 /tmp 中。该目录在启动之间保存文件。\n\n9. 使用异步调用模式避免同步冷启动。\n\n希望这些提示可以帮助你加速 Lambda 函数的初始化!让我知道如果你有任何其他问题。"
            },
            {
                "role":"user",
                "content":"请介绍一下bedrock"
            },
            {
                "role":"ai",
                "content":" Amazon Bedrock是一个机器学习服务,可以帮助您构建和部署基于大语言模型的对话式人工智能应用程序。\n\nBedrock的主要特点和功能包括:\n\n1. 预训练模型库 - Bedrock提供了多个预训练好的对话模型,如Claude等,开箱即用。\n\n2. 自定义模型微调 - 您可以使用自己的数据集对这些预训练模型进行微调,使其适应您的特定应用和对话域。\n\n3. 知识库支持 - 您可以将Bedrock与知识库集成,为对话应用提供背景知识和上下文感知能力。\n\n4. 多种对话通道 - Bedrock支持通过语音、文本或多模态方式进行对话交互。\n\n5. 自动评估和日志记录 - Bedrock会自动评估对话质量,并记录会话日志以进行分析。\n\n6. 简单易用的API - Bedrock提供了简单的API来部署和管理对话模型,无需机器学习专业知识。\n\n7. 完全托管的云服务 - 作为AWS托管服务,Bedrock使您无需管理任何基础设施。\n\n总的来说,Bedrock通过其预训练模型、自定义微调和知识库支持等功能,可以显著降低构建对话AI系统的门槛,加速部署。它使任何规模的公司都可以利用大语言模型的力量来创建人工智能助手和其他对话应用。"
            },
            {
                "role":"user",
                "content": "今天几号"
            },
            {
                "role":"ai",
                "content":" 抱歉,我没有访问当前日期的方式。作为一个AI助手,我不知道“今天”具体指的是哪一天。我建议您直接问我您想知道的具体日期,例如“2022年2月14日是星期几”。或者您也可以询问能够访问当前日期的人这个问题。请让我知道还有什么可以帮助您的!"
            }
        ]
     
    # endpoint_name = 'internlm2-chat-7b-4bits-2024-02-28-07-08-57-839'
    # model_id = "internlm2-chat-7b"

    endpoint_name = 'internlm2-chat-20b-4bits-2024-03-04-06-32-53-653'
    model_id = "internlm2-chat-20b"
    # entry_type = "market_chain_knowledge_langgraph"

    os.environ['llm_model_id'] = model_id
    os.environ['llm_model_endpoint_name'] = endpoint_name


#     body = {
#         "client_type": "zhenghm-postman-summary",
#         "session_id": "af50b380-abec-4f1a-a6e7-acdbca22ebc9",
#         "time_window": {
#         "start_time": 1709787023.0,
#         "end_time": 1709787263.0
#         },
#         "type": "market_conversation_summary",
#         "temperature": 0.1
# }
#     body = {
#     "client_type": "GCRChat",
#     # "session_id": "961515e9-1d91-402a-8996-aba68f4211c5",
#     "enable_debug": True,
#     "time_window": {
#       "start_time": 1710976467.939,
#       "end_time": 1710994497.327
#     },
#     "type": "market_conversation_summary",
#     "temperature": 0.1
# }
    body = {
            "messages": messages,
            "type": 'market_conversation_summary',
            "mkt_conversation_summary_config": {
                "model_id": model_id,
                "endpoint_name": endpoint_name
            }
            # "model":"chat"
            }
    event = {
        "body": json.dumps(body)
    }
  
    event["requestContext"] = {
        "eventType":"MESSAGE",
        "connectionId":f'test_{int(time.time())}'
    }
    context = None
    main.lambda_handler(event, context)
    # body = json.loads(response["body"])
    # answer = body["choices"][0]["message"]["content"]
    # print(answer)

def code_chat_test():
    session_id = f'test_{int(time.time())}'
    generate_answer(
        "来点复杂的js code", 
        model="chat",  
        stream=True,
        type="market_chain", 
        session_id=session_id
    )
    generate_answer(
        "Lambda冷启动怎么解决", 
        model="knowledge_qa", 
        stream=True,
        type="market_chain", 
        session_id=session_id
    )

            
def market_deploy_test():
    multiturn_strict_qq_test()
    multiturn_chat_test()
    knowledge_qa_test()
    
    generate_answer(
        "今天天气怎么样？", 
        model="auto", 
        stream=True,
        type="market_chain", 
    )
    qq_match_test()

    market_summary_test2()

def dgr_deploy_test():
    os.environ['llm_model_id'] = "anthropic.claude-3-sonnet-20240229-v1:0"
    session_id = f'test_{int(time.time())}'
    questions = [
        "我的产品每分钟发送约20万个事件到网站以发布广告,将这些大量数据实时传输到Amazon Redshift的最佳方式是什么?",
        # '\n将计算资源与Lambda函数部署在相同AZ是否会降低延迟？'
        # "Elastic Load Balancing如何启用跨区域负载均衡？",
        # "Amazon VPC默认安全组的默认入站和出站规则?",
        # "每个AWS Site-to-Site VPN 隧道的最大带宽是多少?"
        # "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?",
        # "请问Amazon ECS Fargate支持哪些操作系统和CPU架构?",
        # "如何将镜像推送到 Amazon Elastic Container Registry？",
        # "Amazon S3 静态网站端点支持 HTTPS吗？",
        # "如何禁用QuickSight账户中的电子邮件邀请新用户选项？",
        # "如何解决Linux实例在升级和重启后未通过实例检查、无法连接的问题？"
        # "如何在控制台配置Amazon Kendra使用RDS MySQL作为数据源？",
        # "给我一个Amazon Redshift的DescribeClusters API的使用示例",
        # "将AMI从一个区域复制到另一个区域的API是什么？"
        # '请问Amazon Sagemaker jumpstart 和Amazon Bedrock 有什么不同？'
        # '请问亚马逊云科技中国区域的S3和EC2的价格',
        # '我想用ec2搭建my sql数据库，想要放在公网，想问一下是否有安全访问的最佳实践？'
    ]

    endpoint_name = 'internlm2-chat-20b-4bits-continuous-bat-2024-03-23-16-25-28-881'
    model_id = "internlm2-chat-20b"

    rag_parameters = {
        "get_contexts": True,
        "response_config": {
            # context return with chunk
            "context_return_with_chunk": True
        },
        # "query_process_config": {
        #     "query_length_threshold": 1,
        #     "query_rewrite_config": {
        #         "model_id": model_id,
        #         "endpoint_name": endpoint_name,
        #     }
        # }
    }
    for question in questions:
        generate_answer(
            question, 
            stream=True,
            type="dgr",
            rag_parameters=rag_parameters
            # session_id=session_id
        )
    

if __name__ == "__main__":
    # market_summary_test()
    # multiturn_chat_test()
    # market_summary_test()
    # code_chat_test()
    # market_summary_test2()
    # market_deploy_test()
    # market_deploy_cn_test()

    # generate_answer(
    #     "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", 
    #     model="chat", 
    #     stream=True,
    #     type="market_chain", 
    # )
    # market_deploy_test()
    # knowledge_qa_test()
    # r = generate_answer(
    #     "怎么开发票？", 
    #     model="knowledge_qa", 
    #     stream=True,
    #     type="market_chain", 
    # )
    # knowledge_qa_test()

    
    # market_deploy_test()
    # test_baichuan_model()
    # market_summary_test2()
    # test_internlm_model()
    # dgr_deploy_test()
    test_internlm_model_mkt_knowledge_entry()
    # test_internlm_model_mkt_knowledge_entry_with_conversation()
    # test_internlm_model_mkt_knowledge_entry_with_conversation_batch()
    # test_internlm_model_mkt_knowledge_entry_qq_match()
    # test_internlm_model_mkt_knowledge_entry_langgraph()
    # test_baichuan_model()
    
    # market_deploy_test()
    # dgr
    # dgr_deploy_test()
    # generate_answer(
    #     # "如何将Kinesis Data Streams配置为AWS Lambda的事件源？",
    #     # "Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?",
    #     "什么是Amazon bedrock？",
    #     model="knowledge_qa", 
    #     stream=True,
    #     type="dgr", 
    #     rag_parameters=dict(
    #         get_contexts = True,
    #         retriever_config={
    #             "retriever_top_k": 1,
    #             "chunk_num": 2,
    #             "using_whole_doc": False,
    #             "reranker_top_k": 10,
    #             "enable_reranker": True
    # },
    # )
    # )

    # r = generate_answer("请写一首诗",model='caht')
    # multiturn_chat_test()
    # generate_answer(
    #     "我想调用Amazon Bedrock中的基础模型，应该使用什么API?",
    #     stream=True,
    #     model='auto'
    #     )
    # LLM
    # generate_answer("Amazon EC2 提供了哪些功能来支持不同区域之间的数据恢复?", model="knowledge_qa", stream=False)
    # generate_answer("什么是 CodeDeploy？", model="knowledge_qa", stream=True)
    # Q-Q
    # generate_answer("在相同的EMR Serverless应用程序中，不同的Job可以共享Worker吗？", model="knowledge_qa", stream=True)
    # generate_answer("polly是什么？", model="auto")
    # generate_answer("DynamoDB API\n要使用 Amazon DynamoDB，您的应用程序必须使用一些简单的 API 操作。下面汇总了这些操作（按类别组织）。")
    # generate_answer("polly是什么？")
    # mkt
    # generate_answer("ECS容器中的日志，可以配置输出到S3上吗？")
    # generate_answer("只要我付款就可以收到发票吗")
    # generate_answer("找不到发票怎么办")
    # generate_answer("发票内容有更新应怎么办", model="strict_q_q")
    # generate_answer("发票内容有更新应怎么办", type="common", stream=False)
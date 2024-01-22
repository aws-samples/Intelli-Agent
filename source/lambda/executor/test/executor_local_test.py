import json
import sys
import csv
import os 
import time 
os.environ['AWS_PROFILE'] = "atl"
os.environ["AWS_REGION"] = "us-west-2"
os.environ['AWS_DEFAULT_REGION'] = "us-west-2"
os.environ['AWS_REGION'] = "us-west-2"
import logging
log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

sys.path.append("llm-bot/source/lambda/executor/utils")
sys.path.append("llm-bot/source/lambda/executor")
sys.path.append("utils")
sys.path.append(".")
import aos_utils
# from requests_aws4auth import AWS4Auth
# import boto3
# region = "us-east-1"
# credentials = boto3.Session().get_credentials()
# aos_utils.awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

from dotenv import load_dotenv
load_dotenv()
# import os
# region = os.environ["AWS_REGION"]
# print(region)
import main
import os
aos_index_dict = json.loads(os.environ.get("aos_index_dict", ""))
print(f"aos index {aos_index_dict}")

class DummyWebSocket:
    def post_to_connection(self,ConnectionId,Data):
        data = json.loads(Data)
        message = data['choices'][0].get('message',None)
        ret = data
        if message is not None:
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
                print('sources: ',ret['choices'][0]['knowledge_sources'])

main.ws_client = DummyWebSocket()

def generate_answer(query,
                    temperature=0.7,
                    enable_debug=True,
                    retrieval_only=False,
                    type="market_chain",
                    model="knowledge_qa",
                    stream=False,
                    retriever_index="test-index",
                    session_id=None):
    event = {
        "body": json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": temperature,
                "enable_debug": enable_debug,
                "retrieval_only": retrieval_only,
                "retriever_index": retriever_index,
                "type": type,
                "model": model,
                "session_id":session_id
            }
        )
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

def market_deploy_test():
    multiturn_chat_test()
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
        "今天天气怎么样？", 
        model="auto", 
        stream=True,
        type="market_chain", 
    )
    generate_answer(
        "IoT Core是否支持Qos2？", 
        model="auto", 
        stream=True,
        type="market_chain", 
    )


if __name__ == "__main__":
    market_deploy_test()
    # dgr
    # generate_answer("Amazon Fraud Detector 中'entityId'和'eventId'的含义与注意事项")
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
    # generate_answer("发票内容有更新应怎么办")
    # generate_answer("发票内容有更新应怎么办", type="common", stream=False)
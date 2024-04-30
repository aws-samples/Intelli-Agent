import json
import sys
import csv
import os 
import time 
import uuid

from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__),'.env_bot_uw2')
)

import logging
log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

sys.path.append("./lambda_main")
import main
import os
from collections import defaultdict

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
            print(message.keys())

main.ws_client = DummyWebSocket()

def generate_answer(query=None,
                    messages=None,
                    # temperature=0.7,
                    enable_debug=True,
                    retrieval_only=False,
                    type="common",
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
            "enable_debug":False,
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
        # debug_info = body["debug_info"]
        debug_info = ""
        return (answer,
                knowledge_sources,
                debug_info)

if __name__ == "__main__":
    generate_answer("ECS容器中的日志，可以配置输出到S3上吗？")
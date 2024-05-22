import json
import sys
import csv
import os 
import time 
import uuid
import sys
sys.path.append("./layer_logic")
from common_utils.lambda_invoke_utils import invoke_lambda

from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__),'.env')
)

import logging
log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

import lambda_main.main as main
import common_utils.websocket_utils as websocket_utils
import os
from collections import defaultdict

# contexts = defaultdict(str)

class DummyWebSocket:
    def post_to_connection(self,ConnectionId,Data):
        data = json.loads(Data)
        ret = data
        message_type = ret['message_type']
        # print('message_type',message_type)
        if message_type == "START":
            pass
        elif message_type == "CHUNK":
            print(ret['message']['content'],end="",flush=True)
        elif message_type == "END":
            return 
        elif message_type == "ERROR":
            print(ret['message']['content'])
            return 
        elif message_type == "MONITOR":
            print("monitor info: ",ret['message'])

websocket_utils.ws_client = DummyWebSocket()


def generate_answer(query,
                    entry_type="common",
                    stream=False,
                    session_id=None,
                    chatbot_config=None
                    ):
    chatbot_config = chatbot_config or {}


    body = {
            "query": query,
            "entry_type": entry_type,
            "session_id":session_id,
            "chatbot_config": chatbot_config     
            }
    event = {
        "body": json.dumps(body)
    }
    if stream:
        event["requestContext"] = {
            "eventType":"MESSAGE",
            "connectionId":f'test_{int(time.time())}'
        }

    context = None
    response = invoke_lambda(
        lambda_invoke_mode="local",
        lambda_module_path="lambda_main.main",
        event_body=event
    )
    # response = main.lambda_handler(event, context)
    if stream:
        return
    
    if not stream:
        body = json.loads(response["body"])
        print(body)
        return body


def test():
    generate_answer(
        "What is lihoyo's most famous game?",
        stream=True,
        chatbot_config={
            "agent_config":{
                "model_id":"anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs": {"temperature":0.0,"max_tokens":4096},
                "tools":[{"name":"give_final_response"},{"name":"search_lihoyo"}]
        },
        }
    )


if __name__ == "__main__":
    test()
    
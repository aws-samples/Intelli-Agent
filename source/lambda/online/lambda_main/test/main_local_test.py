import sys
import os

from lambda_main.test.main_local_test_retail import multi_turn_test
sys.path.append("./common_logic")
sys.path.append("../job/dep/llm_bot_dep")
from dotenv import load_dotenv
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__),'.env')
)
import json
import time 
from common_utils.lambda_invoke_utils import invoke_lambda
import common_utils.websocket_utils as websocket_utils

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
    session_id = session_id or time.time()


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


def test(chatbot_mode="agent",session_id=None,query=None,use_history=True):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 4096}
        }
    chatbot_config = {
        "chatbot_mode": chatbot_mode,
        "use_history": use_history,
        "query_process_config":{
            "conversation_query_rewrite_config":{
                **default_llm_config
            }
        },
        "intent_recognition_config":{
        },
        "agent_config":{
            **default_llm_config,
            "tools":[]
        },
        "tool_execute_config":{
            "knowledge_base_retriever":{
                "retrievers": [
                {
                    "type": "qd",
                    "workspace_ids": [1],
                    "top_k": 10,
                }
                ]
            }
        },
        "chat_config":{
            **default_llm_config,
        },
        "rag_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qd",
                        "workspace_ids": [],
                        "config": {
                            "top_k": 20,
                            "using_whole_doc": True,
                        }
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz"
                        }
                    }
                ],
            },
            "llm_config":{
                **default_llm_config,
            }
        }
    }
    
    generate_answer(
        query,
        stream=True,
        session_id=session_id,
        chatbot_config=chatbot_config
    )

def test_multi_turns():
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"今天星期几？", "use_history":True},
        {"query":"今天星期三", "use_history":True},
        {"query":"今天星期几", "use_history":False},
        {"query":"我们进行了几轮对话", "use_history":True},
    ]

    
    # goods_id = 653918410246
    # user_queries = [
    #     {"query":"http://item.taobao.com/item.htm?id=653918410246","goods_id":653918410246},
    #     {"query":"跑步有没有问题","goods_id":653918410246},
    #     {"query":"https://detail.tmall.com/item.htm?id=760740990909","goods_id":760740990909},
    #     {"query":"160 110穿多大","goods_id":760740990909},
    #     {"query":"我换个号","goods_id":760740990909}
    # ]


    for query in user_queries:
        if isinstance(query,str):
            query = {"query":query}
        test(
            chatbot_mode='chat',
            session_id=session_id,
            query=query['query'],
            use_history=query['use_history']
        )
  
if __name__ == "__main__":
    # test(chatbot_mode="agent")
    test_multi_turns()
    

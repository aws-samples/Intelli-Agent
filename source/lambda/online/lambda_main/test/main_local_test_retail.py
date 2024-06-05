import sys
import os
import tqdm
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
import pandas as pd 

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
                    entry_type="retail",
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
        # print(body)
        return body


def test(chatbot_mode="chat",session_id=None,query=None,goods_id=None):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 4096}
        }
    chatbot_config = {
        "goods_id":goods_id,
        "chatbot_mode": chatbot_mode,
        "use_history": True,
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
        },
        "rag_product_aftersales_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu'],
                        "config": {
                            "top_k": 2,
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
        },
        "rag_customer_complain_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
                        "config": {
                            "top_k": 2,
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
        },
        "rag_promotion_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
                        "config": {
                            "top_k": 2,
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
    
    session_id = session_id or f"test_{time.time()}"
    query = query or "很浪费时间 出库的时候也不看清楚？"
    session_id = f"test_{time.time()}"
    
    # 售后物流
    #"可以发顺丰快递吗？",
    # 客户抱怨
    # "很浪费时间 出库的时候也不看清楚？",
    # 促销查询
    # "评论有惊喜吗？",
    generate_answer(
        query,
        stream=True,
        session_id=session_id,
        chatbot_config=chatbot_config
    )


def batch_test():
    data_file = "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/customer_poc/anta/conversation_turns.csv"
    data = pd.read_csv(data_file).to_dict(orient='records')
    session_prefix = f"anta_test_{time.time()}"
    default_llm_config = {
        'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 4096}
        }
    chatbot_config = {
        "chatbot_mode": "agent",
        "use_history": True,
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
        "rag_product_aftersales_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu'],
                        "config": {
                            "top_k": 2,
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
        },
        "rag_customer_complain_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
                        "config": {
                            "top_k": 2,
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
    data = data[:1]
    data_to_save = []
    for datum in tqdm.tqdm(data,total=len(data)):
        print("=="*50)
        print(f'query: {datum["user_msg"]}')
        session_id = f"{session_prefix}_{datum['desensitized_cnick']}"
        chatbot_config.update({"goods_id":datum['product_ids']})

        r = generate_answer(
            datum['user_msg'],
            stream=False,
            session_id=session_id,
            chatbot_config=chatbot_config
        )
        datum['agent_intent_type'] = r.get('current_agent_intent_type',None)
        datum['ai_msg'] = r['message']['content']
        datum['session_id'] = session_id
        datum['query_rewrite'] = r.get('query_rewrite',None)
        datum['intention_fewshot_examples'] = r.get('intention_fewshot_examples',None)
        data_to_save.append({
            "session_id": datum['desensitized_cnick'],
            "goods_id": datum['product_ids'],
            "create_time": datum['create_time'],
            "user_msg":datum['user_msg'],
            "ai_msg": datum['ai_msg'],
            "ai_intent": datum['agent_intent_type'],
            "intent": None,
            "accuracy": None,
            "rewrite_query": datum['query_rewrite'],
            "ddb_session_id": session_id,
            "comments": None,
            "owner": None
        })
    # session_id, goods_id, create_time, user_msg, ai_msg, ai_intent, intent, accuracy,rewrite_query
    
    pd.DataFrame(data_to_save).to_csv(
        f'{session_prefix}_anta_test_{len(data_to_save)}.csv',
        index=False
        )


if __name__ == "__main__":
    # batch_test()
    test(
        chatbot_mode='agent',
        goods_id="675124761798",
        query="平常41吗，这款鞋需要多少码"
    )
    # test(
    #     chatbot_mode='agent',
    #     session_id="anta_test_1717567916.145038_cn****0099",
    #     query="你家鞋子开胶了，怎么处理"
    #     )
    

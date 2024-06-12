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
            print(ret['message']['content'],flush=True)
            return 
        elif message_type == "MONITOR":
            print("monitor info: ",ret['message'],flush=True)

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


def test(chatbot_mode="agent",session_id=None,query=None,goods_id=None,use_history=True):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 1000}
        }
    # default_llm_config = {
    #     'model_id': '"gpt-3.5-turbo-0125',
    #     'model_kwargs': {
    #         'temperature': 0.5, 'max_tokens': 4096}
    #     }
    chatbot_config = {
        "goods_id":goods_id,
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
    # session_id = f"test_{time.time()}"
    
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


def test_multi_turns():
    session_id = f"anta_test_{time.time()}"
    # goods_id = "756327274174"
    # user_queries = [
    #     "http://item.taobao.com/item.htm?id=756327274174",
    #     "亲，平常穿37联系多大码",
    #     "还会有货吗？"
    # ]
    
    # goods_id = "745288790794"
    # user_queries = [
    #     "https://detail.tmall.com/item.htm?id=745288790794",
    #     "为啥要运费？",
    #     "现在怎么还还有鞋啊",
    #     "不是一个地址发货？\n买鞋了啊\n鞋和袜子不是一个地方发货吗？",
    #     "https://img.alicdn.com/imgextra/i2/O1CN01B7yi6r1CavknQAhuz_!!0-amp.jpg",
    #     "为啥要运费呢",
    #     "我也么有只买袜子啊\n你们系统设定有问题吧\n原来没遇到过这种情况啊",
    #     "好的",
    #     "https://item.taobao.com/item.htm?id=725289865739\n一个订单可以分开发两个地址吗",
    #     "https://img.alicdn.com/imgextra/i1/O1CN0160oEXO1CavkoLIirq_!!0-amp.jpg",
    #     "这个券我抢到了，下单的时候自动使用吗",
    #     "正确",
    #     "发什么快递？今天能发货吗"
    # ]


    goods_id = 766158164989
    # {"query":"杨幂同款裤子有吗","goods_id":},
    # user_queries = [
    #     {"query":"https://detail.tmall.com/item.htm?id=766158164989","goods_id":766158164989},
    #     {"query":"155.厘米125斤", "goods_id":766158164989},
    #     {"query":"http://item.taobao.com/item.htm?id=766277539992","goods_id":766277539992},
    #     {"query":"亲，这个大人能穿吗\n165身高的话可以换165m吗","goods_id":766277539992},
    #     {"query":"https://item.taobao.com/item.htm?id=766277539992\n好吧/:018","goods_id":766277539992}
    # ]

    user_queries = [
        {"query":"杨幂同款裤子有吗","goods_id":763841838892}
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
            chatbot_mode='agent',
            session_id=session_id,
            query=query['query'],
            goods_id=query.get("goods_id",None) or goods_id
        )


def batch_test():
    data_file = "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/customer_poc/anta/conversation_turns.csv"
    data = pd.read_csv(data_file).to_dict(orient='records')
    session_prefix = f"anta_test_{time.time()}"
    default_llm_config = {
        # 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        # 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_id': 'mistral.mixtral-8x7b-instruct-v0:1',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 4096}
        }
    chatbot_config = {
        "chatbot_mode": "agent",
        "use_history": True,
        "enable_trace": True,
        "default_llm_config":default_llm_config,
        "intention_config": {
            "query_key": "query"
        }
    }
    # data = data]
    data_to_save = []
    for datum in tqdm.tqdm(data,total=len(data)):
        print("=="*50,flush=True)
        print(f'query: {datum["user_msg"]},\ngoods_id: {datum["product_ids"]}',flush=True)
        
        if datum["product_ids"]:
            try:
                product_ids = int(datum["product_ids"])
            except:
                import traceback
                print(f"error product_ids:\n {traceback.format_exc()}")
                product_ids = datum["product_ids"]

        else:
            product_ids = None
        session_id = f"{session_prefix}_{datum['desensitized_cnick']}"
        chatbot_config.update({"goods_id":product_ids})
        try:
            r = generate_answer(
                datum['user_msg'],
                stream=False,
                session_id=session_id,
                chatbot_config=chatbot_config,
                entry_type="retail"
            )
            ai_msg = r['message']['content']
        except:
            import traceback
            print(f"error run:\n {traceback.format_exc()}",flush=True)
            ai_msg = None
            r = {}
        return 

        datum['agent_intent_type'] = r.get('current_agent_intent_type',None)
        datum['ai_msg'] = ai_msg
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
        print()
    # session_id, goods_id, create_time, user_msg, ai_msg, ai_intent, intent, accuracy,rewrite_query
    
        pd.DataFrame(data_to_save).to_csv(
            f'{session_prefix}_anta_test_mixtral8x7b_{len(data)}.csv',
            index=False
            )

def multi_turn_test():
    # # 0099 test
    # session_id = f"0099_test_{time.time()}"
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="你家鞋子开胶了？怎么处理"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="我在得物购买的"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="如果在你家买的鞋子，出现质量问题你们怎么处理"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="如果在你家买的鞋子，出现质量问题你们怎么处理"
    #     )
    # # 0098 test
    # session_id = f"0098_test_{time.time()}"
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="为啥要运费？"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="现在怎么还还有鞋啊？"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id=session_id,
    #     query="不是一个地址发货？买鞋了啊 鞋和袜子不是一个地方发货的吗？"
    #     )
    # 0099 test
    session_id = f"0068_test_{time.time()}"
    goods_id = 756327274174
    test(
        chatbot_mode='chat',
        session_id=session_id,
        goods_id=goods_id,
        query="亲，平常穿37联系多大码",
        use_history=True
        )
    test(
        chatbot_mode='chat',
        session_id=session_id,
        goods_id=goods_id,
        query="还会有货吗？"
        )
    # 


if __name__ == "__main__":
    test_multi_turns()

    # batch_test()
    # batch_test()
    # test(
    #     chatbot_mode='agent',
    #     goods_id="675124761798",
    #     query="平常41吗，这款鞋需要多少码"
    # )
    # test(
    #     chatbot_mode='agent',
    #     goods_id="675124761798",
    #     query="平常41吗，这款鞋需要多少码"
    # )
        # query="你家鞋子开胶了，怎么处理？"
    # test(
    #     chatbot_mode='agent',
    #     query="g5.2xlarge ec2的价格是多少"
    #     )
    # test(
    #     chatbot_mode='agent',
    #     session_id="anta_test_1717567916.145038_cn****0099",
    #     query="为什么这个商品需要支付运费？"
    #     )
    # # multi-turn test
    # test(
    #     chatbot_mode='agent',
    #     session_id="anta_test_1717567916.145038_cn****0099",
    #     query="为什么这个商品需要支付运费？"
    #     )
    # multi-turn test

    # multi_turn_test()
    

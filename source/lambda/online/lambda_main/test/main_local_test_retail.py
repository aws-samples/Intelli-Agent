from local_test_base import generate_answer
import time 
import json 
import pandas as pd 
import tqdm 
def test(chatbot_mode="agent",session_id=None,query=None,goods_id=None,use_history=True):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 1000}
        }

    chatbot_config = {
        "goods_id":goods_id,
        "chatbot_mode": chatbot_mode,
        "use_history": use_history
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

    # user_queries = [
    #     {"query":"杨幂同款裤子有吗","goods_id":763841838892}
    # ]

    # user_queries = [
    #     {"query":"你家鞋子开胶了\n怎么处理","goods_id":743891340644},
    #     # {"query":"我在得物买的","goods_id":743891340644}
    # ]


    # user_queries = [
    #     {"query":"https://detail.tmall.com/item.htm?id=748090908717","goods_id":748090908717},
    #     {"query":"177 65kg多大","goods_id":748090908717},
    #     # {"query":"我在得物买的","goods_id":743891340644}
    # ]
    # user_queries = [
    #     {"query":"人工","goods_id":712058889741},
    #     {"query":"人工","goods_id":712058889741},
    #     {"query":"人工 https://detail.tmall.com/item.htm?id=712058889741","goods_id":712058889741},
    #     {"query":"这个最大码能穿到多少斤","goods_id":712058889741},
    #     {"query":"好的 我现在168 是个孕妇 身高174 就肚子大点 身上没那么胖 我该穿多大的 Xxl 就行了吧","goods_id":712058889741},
    #     {"query":"168","goods_id":712058889741},
    #     {"query":"但是没有码了","goods_id":712058889741},
    #     {"query":"Xl能行不","goods_id":712058889741},
    #     {"query":"Xxxl是不是太大了","goods_id":712058889741}
    # ]
    # user_queries = [
    #     {"query":"http://item.taobao.com/item.htm?id=666167992985","goods_id":666167992985},
    #     {"query":"在吗","goods_id":666167992985},
    #     {"query":"断码吗","goods_id":666167992985}
    # ]
    # user_queries = [
    #     {
    #         "query":"http://item.taobao.com/item.htm?id=743353945710","goods_id":743353945710
    #     },
    #     {
    #         "query":"请问你们是哪里发货","goods_id":743353945710
    #     }
    # ]
    # user_queries = [
    #     {"query":"能发顺丰嘛？","goods_id":641874887898},
    # ]

    # user_queries = [
    #     {"query":"好的","goods_id": 745288790794}
    # ]
    user_queries = [
        {"query":"这款还会有货吗？","goods_id": 760601512644},
        {"query":"我穿180的","goods_id": 760601512644}
    ]
    # user_queries = [
    #     {"query":"正确","goods_id": 745288790794}
    # ]
    
    # goods_id = 653918410246
    # user_queries = [
    #     {"query":"http://item.taobao.com/item.htm?id=653918410246","goods_id":653918410246},
    #     {"query":"跑步有没有问题","goods_id":653918410246},
    #     {"query":"https://detail.tmall.com/item.htm?id=760740990909","goods_id":760740990909},
    #     {"query":"160 110穿多大","goods_id":760740990909},
    #     {"query":"我换个号","goods_id":760740990909}
    # ]
    default_llm_config = {
        # 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        # 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        # 'model_id':"glm-4-9b-chat",
        # "endpoint_name": "glm-4-9b-chat-2024-06-18-07-37-03-843",
        "model_id": "qwen2-72B-instruct",
        "endpoint_name":  "Qwen2-72B-Instruct-AWQ-2024-06-25-02-15-34-347",
        # 'model_id': 'mistral.mixtral-8x7b-instruct-v0:1',
        'model_kwargs': {'temperature': 0.1}
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
    for query in user_queries:
        if isinstance(query,str):
            query = {"query":query}
        r = generate_answer(
               query=query['query'],
               stream=False,
                session_id=session_id,
                chatbot_config={**chatbot_config,"goods_id": query.get("goods_id")},
                entry_type="retail"
        )
        print(r)


def batch_test():
    data_file = "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/customer_poc/anta/conversation_turns.csv"
    data = pd.read_csv(data_file).to_dict(orient='records')
    session_prefix = f"anta_test_{time.time()}"
    default_llm_config = {
        # 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        # 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        # 'model_id': 'mistral.mixtral-8x7b-instruct-v0:1',
        # 'model_id':"glm-4-9b-chat",
        # "endpoint_name": "glm-4-9b-chat-2024-06-18-07-37-03-843",
        "model_id": "qwen2-72B-instruct",
        "endpoint_name":  "Qwen2-72B-Instruct-AWQ-2024-06-25-02-15-34-347",
        'model_kwargs': {
            'temperature': 0.1, 'max_tokens': 1000}
        }
    chatbot_config = {
        "chatbot_mode": "agent",
        "use_history": True,
        "enable_trace": True,
        "default_llm_config": default_llm_config,
        "intention_config": {
            "query_key": "query"
        }
    }
    # data = data]
    data_to_save = []
    for datum in tqdm.tqdm(data,total=len(data)):
        print("=="*50,flush=True)
        start_time = time.time()
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

            print('r: ',r)
            
            ai_msg = r['message']['content'].strip().rstrip("<|user|>").strip()
        except:
            import traceback
            print(f"error run:\n {traceback.format_exc()}",flush=True)
            ai_msg = None
            r = {}

        datum['agent_intent_type'] = r.get('current_agent_intent_type',None)
        datum['ai_msg'] = ai_msg
        datum['session_id'] = session_id
        datum['query_rewrite'] = r.get('query_rewrite',None)
        datum['intention_fewshot_examples'] = r.get('intention_fewshot_examples',None)
        if ai_msg:
            datum['elpase_time'] = time.time()-start_time
        else:
            datum['elpase_time'] = None
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
            "elpase_time":datum['elpase_time'],
            "ddb_session_id": session_id,
            "comments": None,
            "owner": None,
            "model_id": default_llm_config['model_id']
        })
    # session_id, goods_id, create_time, user_msg, ai_msg, ai_intent, intent, accuracy,rewrite_query
    
        pd.DataFrame(data_to_save).to_csv(
            f'{session_prefix}_anta_test_qwen2-72b-instruct_{len(data)}.csv',
            index=False
        )

def test_multi_turns_pr(mode="agent"):
    session_id = f"anta_multiturn_test_{time.time()}"
    user_queries = [
        {"query":"能发顺丰嘛？","goods_id":641874887898, "use_history":True},
        {"query":"我170能穿吗？","goods_id":641874887898, "use_history":True},
    ]

    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
    }
    chatbot_config = {
        "chatbot_mode": mode,
        "enable_trace": True,
        "default_llm_config":default_llm_config,
        "intention_config": {
            "query_key": "query"
        }
    }
    for query in user_queries:
        if isinstance(query,str):
            query = {"query":query}
        chatbot_config['use_history'] = query['use_history']
        generate_answer(
               query=query['query'],
               stream=True,
               session_id=session_id,
               chatbot_config={**chatbot_config,"goods_id": query.get("goods_id")},
               entry_type="retail"
        )

def complete_test():
    print("start test in chat mode")
    test_multi_turns_pr("chat")
    print("finish test in chat mode")
    print("start test in rag mode")
    test_multi_turns_pr("rag")
    print("finish test in rag mode")
    print("start test in agent mode")
    test_multi_turns_pr("agent")
    print("finish test in agent mode")


if __name__ == "__main__":
    # complete_test()
    # test_multi_turns()
    batch_test()
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
    

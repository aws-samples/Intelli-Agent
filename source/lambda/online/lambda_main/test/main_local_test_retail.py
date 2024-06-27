from email import message
from local_test_base import generate_answer,similarity_calculate
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
    user_queries = [
        {"query":"今天怎么还没有发货","goods_id": 714845988113}
    ]
    
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
        'model_kwargs': {'temperature': 0.01}
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
        print(f"ans: {r['message']['content']}")


def batch_test(data_file, count=1000,add_eval_score=True):
    data = pd.read_csv(data_file).fillna("").to_dict(orient='records')
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
            'temperature': 0.01, 'max_tokens': 1000}
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
    for datum in tqdm.tqdm(data[:count], total=min(len(data), count)):
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
            trace_infos = r.get("trace_infos",[])
            
            ai_msg = r['message']['content'].strip().rstrip("<|user|>").strip()
        except:
            import traceback
            print(f"error run:\n {traceback.format_exc()}",flush=True)
            ai_msg = None
            r = {}
            trace_infos=None

        datum['agent_intent_type'] = r.get('current_agent_intent_type',None)
        datum['ai_msg'] = ai_msg
        datum['session_id'] = session_id
        datum['query_rewrite'] = r.get('query_rewrite',None)
        datum['intention_fewshot_examples'] = r.get('intention_fewshot_examples',None)
        if ai_msg:
            datum['elpase_time'] = time.time()-start_time
        else:
            datum['elpase_time'] = None
        
        ground_truth = str(datum.get("ground truth","")).strip()
        print('ground_truth: ',ground_truth,flush=True)
        sim_score = None
        if add_eval_score and datum['ai_msg'] and ground_truth:
            sim_score = similarity_calculate(str(datum['ai_msg']),str(ground_truth))

        data_to_save.append({
            "session_id": datum['desensitized_cnick'],
            "goods_id": datum['product_ids'],
            "create_time": datum['create_time'],
            "user_msg":datum['user_msg'],
            "ai_msg": datum['ai_msg'],
            "ground truth": ground_truth,
            "sim_score_with_ground_truth": sim_score,
            "trace_infos":str(trace_infos),
            "ai_intent": datum['agent_intent_type'],
            "intent": None,
            "accuracy": None,
            "rewrite_query": datum['query_rewrite'],
            "elpase_time":datum['elpase_time'],
            # "ddb_session_id": session_id,
            "comments": None,
            "owner": None,
            "model_id": default_llm_config['model_id'],
            
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
        r = generate_answer(
               query=query['query'],
               stream=True,
               session_id=session_id,
               chatbot_config={**chatbot_config,"goods_id": query.get("goods_id")},
               entry_type="retail"
        )
        print(r['message']['content'])

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
    batch_test(data_file="/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/customer_poc/anta/anta_batch_test - batch-test-csv-file-626.csv")
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
    

from email import message
from local_test_base import generate_answer,similarity_calculate,auto_evaluation_with_claude
import time 
import json 
import pandas as pd 
import queue 
from threading import Thread
import tqdm 
from datetime import datetime


CREATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
CREATE_TIME_FORMAT_2 = '%Y-%m-%d%H:%M:%S.%f'

def _test_multi_turns(user_queries, record_goods_id=False):
    session_id = f"anta_test_{time.time()}"
    
    default_llm_config = {
        # 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        # 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        # 'model_id':"glm-4-9b-chat",
        # "endpoint_name": "glm-4-9b-chat-2024-06-18-07-37-03-843",
        # "model_id": "qwen2-72B-instruct",
        # "endpoint_name":  "Qwen2-72B-Instruct-AWQ-2024-06-25-02-15-34-347",
        # "model_id": "qwen2-7B-instruct",
        # "endpoint_name":  "Qwen2-7B-Instruct-AWQ-2024-07-10-09-49-39-020",
        "model_id": "qwen1_5-32B-instruct",
        "endpoint_name":  "Qwen1-2024-07-10-03-35-21-876",
        # "endpoint_name": 'Qwen2-72B-Instruct-GPTQ-Int4-2024-06-30-05-59-54-352',
        # "endpoint_name":  "Qwen2-72B-Instruct-AWQ-without-yarn-2024-06-29-12-31-04-818",
        # 'model_id': 'mistral.mixtral-8x7b-instruct-v0:1',
        'model_kwargs': {
            'temperature': 0.01, 
            'max_tokens': 1000,
            "repetition_penalty":1.05,
            "stop_token_ids": [151645,151643],
            "stop":["<|endoftext|>","<|im_end|>"],
            "top_k":20,
            "seed":42,
            'top_p': 0.8       
            }
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
    if record_goods_id:
        chatbot_config["history_config"]=['goods_id']
    query_answers = []
    for query in user_queries:
        if isinstance(query,str):
            query = {"query":query}
        
        create_time = query.get('create_time',datetime.now().strftime(CREATE_TIME_FORMAT))
        try:
            create_time = datetime.strptime(create_time, CREATE_TIME_FORMAT)
        except ValueError:
            create_time = datetime.strptime(create_time, CREATE_TIME_FORMAT_2)

        create_time = create_time.strftime(CREATE_TIME_FORMAT)

        r = generate_answer(
               query=query['query'].replace("/:018",""),
            #    create_time=,
               stream=False,
                session_id=session_id,
                chatbot_config={**chatbot_config,"goods_id": query.get("goods_id"),"create_time":create_time},
                entry_type="retail"
        )
        query_answers.append((query['query'],r['message']['content']))
    
    print()
    print()
    for query,ans in query_answers:
        print("="*50)
        print(f"human: {query}\nAi: {ans}")



def test_multi_turns():
    user_queries = [
        {"query":"我平时穿37，这个鞋合适吗？","goods_id": 756327274174},
        {"query":"需要运费吗？","goods_id": 743891340644},
        {"query":"我已经下完单了，什么时候发货？","goods_id": 743891340644},
        {"query":"身高170，能穿吗？","goods_id": 743891340644},
        {"query":"45kg","goods_id": 743891340644}]
    return _test_multi_turns(user_queries)


def test_multi_turns_anta(
        session_id,
        user_queries_path="/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/source/lambda/online/session_user_queries.json",
        record_goods_id=False
        ):
    user_queries = json.load(open(user_queries_path))[session_id]
    return _test_multi_turns(user_queries,record_goods_id=record_goods_id)
    

def batch_test(data_file, count=1000,add_eval_score=True,record_goods_id=False):
    data = pd.read_csv(data_file).fillna("").to_dict(orient='records')
    session_prefix = f"anta_test_{time.time()}"
    default_llm_config = {
        # 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        # 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        # 'model_id': 'mistral.mixtral-8x7b-instruct-v0:1',
        # 'model_id':"glm-4-9b-chat",
        # "endpoint_name": "glm-4-9b-chat-2024-06-18-07-37-03-843",
        "model_id": "qwen2-72B-instruct",
        "endpoint_name": "Qwen2-72B-Instruct-AWQ-2024-06-25-02-15-34-347",
        # "model_id": "qwen2-7B-instruct",
        # "endpoint_name":  "Qwen2-7B-Instruct-AWQ-2024-07-10-09-49-39-020",
        # "model_id": "qwen1_5-32B-instruct",
        # "endpoint_name":  "Qwen1-2024-07-10-03-35-21-876",
        
        # "endpoint_name":  "Qwen2-72B-Instruct-AWQ-without-yarn-2024-06-29-12-31-04-818",
        'model_kwargs': {
            'temperature': 0.01, 'max_tokens': 800,
            "repetition_penalty":1.05,
            "stop_token_ids": [151645,151643] ,
            "stop":["<|endoftext|>","<|im_end|>"],
            "top_k":1,
            'top_p': 0.8,
            "seed":42  
            }
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
    if record_goods_id:
        chatbot_config["history_config"]=['goods_id']

    if record_goods_id:
        chatbot_config["history_config"]=['goods_id']

    save_csv_path = f'anta_test/{session_prefix}_anta_test_{default_llm_config["model_id"]}_{len(data)}.csv'


    def _auto_eval_thread_helper(ret_q:queue.Queue):
        data_to_save = []
        while True:
            datum = ret_q.get()
            if datum is None:
                return 
            ground_truth = datum['ground_truth']
            print('ground_truth: ',ground_truth,flush=True)
            sim_score = None
            if add_eval_score and datum['ai_msg'] and ground_truth:
                try:
                    # sim_score = similarity_calculate(str(datum['ai_msg']),str(ground_truth))
                    sim_score = auto_evaluation_with_claude(
                        ref_answer=str(ground_truth),
                        model_answer=str(datum['ai_msg'])
                        )
                except Exception as e:
                    print('auto evaluation error: ',str(e),(str(ground_truth),str(datum['ai_msg'])))
                    

            data_to_save.append({
                "session_id": datum['desensitized_cnick'],
                "goods_id": datum['product_ids'],
                "create_time": datum['create_time'],
                "user_msg":datum['user_msg'],
                "ai_msg": datum['ai_msg'],
                "ground truth": ground_truth,
                "sim_score_with_ground_truth": sim_score,
                "ai_intent": datum['agent_intent_type'],
                "rewrite_query": datum['query_rewrite'],
                "trace_infos":str(trace_infos),
                # "intent": None,
                # "accuracy": None,
                "elpase_time":datum['elpase_time'],
                # "ddb_session_id": session_id,
                # "comments": None,
                # "owner": None,
                "model_id": default_llm_config['model_id'],
                
            })
            # session_id, goods_id, create_time, user_msg, ai_msg, ai_intent, intent, accuracy,rewrite_query
            pd.DataFrame(data_to_save).to_csv(
                save_csv_path,
                index=False
            )

    
    ret_q = queue.Queue()

    t = Thread(target=_auto_eval_thread_helper,args=(ret_q,))
    t.start()

    # data = data]
    # data_to_save = []
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
        

        create_time = datum.get('create_time',datetime.now().strftime(CREATE_TIME_FORMAT))
        try:
            create_time = datetime.strptime(create_time, CREATE_TIME_FORMAT)
        except ValueError:
            create_time = datetime.strptime(create_time, CREATE_TIME_FORMAT_2)
        create_time = create_time.strftime(CREATE_TIME_FORMAT)

        chatbot_config.update({"goods_id":product_ids,"create_time":create_time})
        try:
            r = generate_answer(
                datum['user_msg'].replace("/:018",""),
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
        datum['ground_truth'] = ground_truth
        ret_q.put(datum)
    
    ret_q.put(None)


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
               stream=False,
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
    test_multi_turns_anta("cn****0094", record_goods_id=True)
    # test_multi_turns()
    # test_multi_turns_0090() 
    # test_multi_turns_0077()
    # test_multi_turns_pr("agent")
    # batch_test(
    #     data_file="/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/customer_poc/anta/anta_batch_test - batch-test-csv-file-626.csv",
    #     record_goods_id=True
    # )
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
    

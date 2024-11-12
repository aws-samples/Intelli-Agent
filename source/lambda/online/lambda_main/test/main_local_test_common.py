from local_test_base import generate_answer
import time


def test(chatbot_mode="agent",
         session_id=None,
         query=None,
         use_history=True,
         only_use_rag_tool=False,
         **kwargs
         ):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5,
            'max_tokens': 4096
        }
    }
    chatbot_config = {
        "chatbot_mode": chatbot_mode,
        "use_history": use_history,
        "default_llm_config": default_llm_config,
        "agent_config": {
            "only_use_rag_tool": only_use_rag_tool
        }
    }

    chatbot_config.update(kwargs)
    generate_answer(
        query,
        stream=True,
        session_id=session_id,
        chatbot_config=chatbot_config,
        entry_type="common",
    )


def test_multi_turns_rag_pr():
    print("complete test for only rag tool mode")
    print("++" * 50)
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "什么是aws ec2",
            "use_history": True
        },
        {
            "query": "什么是sagemaker",
            "use_history": True
        },
    ]

    for query in user_queries:
        print()
        print("==" * 50)
        if isinstance(query, str):
            query = {"query": query}
        test(chatbot_mode='agent',
             session_id=session_id,
             query=query['query'],
             use_history=query['use_history'],
             only_use_rag_tool=True,
             default_index_names={"private_knowledge":["xfg"]}
             )
        print()


def test_multi_turns_chat_pr():
    print("complete test for chat")
    print("++" * 50)
    mode = "chat"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "今天几号",
            "use_history": True
        },
        {
            "query": "你好",
            "use_history": True
        },
        {
            "query": "你今天心情如何",
            "use_history": True
        },
    ]

    for query in user_queries:
        print()
        print("==" * 50)
        if isinstance(query, str):
            query = {"query": query}
        test(chatbot_mode=mode,
             session_id=session_id,
             query=query['query'],
             use_history=query['use_history'])
        print()


def test_multi_turns_agent_pr():
    print("complete test for agent")
    print("++" * 50)
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "什么是s3",
            "use_history": True,
            "enable_trace": True
        },
        {
            "query": "你好",
            "use_history": True,
            "enable_trace": False
        },
        {
            "query": "人工客服",
            "use_history": True,
            "enable_trace": True
        },
        {
            "query": "垃圾",
            "use_history": True,
            "enable_trace": True
        },
        {
            "query": "什么是aws ec2",
            "use_history": True
        },
        {
            "query": "今天天气怎么样",
            "use_history": True,
            "enable_trace": False
        },
        {
            "query": "我在上海",
            "use_history": True,
            "enable_trace": False
        },
    ]

    default_index_names = {
        "intention":[],
        "qq_match": [],
        "private_knowledge": []
    }
    # user_queries = [{
    #         "query": "今天天气怎么样",
    #         "use_history": True,
    #         "enable_trace": False
    #     }]
    # user_queries = [{
    #         # "query": "199乘以98等于多少",
    #         "query": "1234乘以89878等于多少？",
    #         "use_history": True,
    #         "enable_trace": True
    #     }]
    # user_queries = [{
    #         "query": "199乘以98等于多少",
    #         # "query": "介绍一下MemGPT",
    #         "use_history": True,
    #         "enable_trace": True
    #     }]
    user_queries = [
        {
            # "query": "”我爱北京天安门“包含多少个字符?",
            # "query": "What does 245346356356 times 346357457 equal?",  # 1089836033535
            # "query": "9.11和9.9哪个更大？",  # 1089836033535
            "query": "今天天气如何？", 
            # "query": "介绍一下MemGPT",
            "use_history": True,
            "enable_trace": True
        },
        {
            # "query": "”我爱北京天安门“包含多少个字符?",
            # "query": "11133乘以97892395等于多少",  # 1089836033535
            "query": "我在上海", 
            # "query": "介绍一下MemGPT",
            "use_history": True,
            "enable_trace": True
        },
        ]

    # default_index_names = {
    #     "intention":[],
    #     "qq_match": [],
    #     "private_knowledge": []
    # }
    default_llm_config = {
        # "model_id":'anthropic.claude-3-sonnet-20240229-v1:0',
        # 'model_id': "anthropic.claude-3-5-sonnet-20240620-v1:0",
        # 'model_id': "anthropic.claude-3-5-haiku-20241022-v1:0",
        # 'model_id': "us.meta.llama3-2-90b-instruct-v1:0",
        # 'model_id':"mistral.mistral-large-2407-v1:0",
        'model_id':"cohere.command-r-plus-v1:0",
        'model_kwargs': {
            'temperature': 0.01,
            'max_tokens': 4096
        }
    }
    # agent_config={"tools":["python_repl"]}
    agent_config = {}
    agent_config={
        "tools":[
            {
            "lambda_name":"intelli-agent-lambda-tool-example1",
            "name": "count_char",
            "description": "Count the number of chars contained in a sentence.",
            "properties": {
                "phrase": {
                    "type": "string",
                    "description": "The phrase needs to count chars"
                }
            },
            "required": ["phrase"],
            "return_direct":False
            },
            "python_repl"
        ]
    }


# {
#     "agent_config":{
#         "tools":[
#             {
#             "lambda_name":"intelli-agent-lambda-tool-example1",
#             "name": "count_char",
#             "description": "Count the number of chars contained in a sentence.",
#             "properties": {
#                 "phrase": {
#                     "type": "string",
#                     "description": "The phrase needs to count chars"
#                 }
#             },
#             "required": ["phrase"],
#             "return_direct":False
#             },
#             "python_repl"
#         ]
#     }
# }

    for query in user_queries:
        print("==" * 50)
        if isinstance(query, str):
            query = {"query": query}
        test(chatbot_mode=mode,
             session_id=session_id,
             query=query['query'],
             use_history=query['use_history'],
             chatbot_id="admin",
             group_name='Admin',
             only_use_rag_tool=False,
             default_index_names=default_index_names,
             enable_trace = query.get('enable_trace',True),
             agent_config=agent_config,
             default_llm_config=default_llm_config
        )
        print()


def test_qq_case_from_hanxu():
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "ceph怎么挂载",
            "use_history": True
        },
    ]
    default_index_names = {
        "intention":[],
        "qq_match": ['hanxu_test-qq-hanxu_poc'],
        "private_knowledge": []
    }

    for query in user_queries:
        print("==" * 50)
        if isinstance(query, str):
            query = {"query": query}
        test(chatbot_mode=mode,
             session_id=session_id,
             query=query['query'],
             use_history=query['use_history'],
             chatbot_id="hanxu_test",
             group_name='hanxu_test',
             only_use_rag_tool=False,
             default_index_names=default_index_names,
             enable_trace = True
             )
        print()



def complete_test_pr():
    print("start test in agent mode")
    test_multi_turns_agent_pr()
    print("finish test in agent mode")
    print("start test in rag mode")
    test_multi_turns_rag_pr()
    print("finish test in rag mode")
    print("start test in chat mode")
    test_multi_turns_chat_pr()
    # print(srg)
    print("finish test in chat mode")


def bigo_test():
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "可以帮忙看看xx这台机，是不是配置太低还是怎么，感觉没启动几个服务，负载比较高",
            "use_history": False
        },
        {
            "query": "如何申请跳板机和服务器的登录权限",
            "use_history": False
        },
        {
            "query": "问一下sgjump跳板机登录权限怎么申请",
            "use_history": False
        },
        {
            "query": "可以给我开通下gitlab的权限吗",
            "use_history": False
        },
        {
            "query": "需要开通git的账号",
            "use_history": False
        },
        {
            "query": "vscode连接不上远程服务器",
            "use_history": False
        },
        {
            "query": "哈喽，我们这边用vscode连不上服务器，不知道什么原因",
            "use_history": False
        },
    ]
    test_rag_system_prompt = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
    <guidelines>
    - NERVER say "根据搜索结果/大家好/谢谢/根据这个文档...".
    - 回答简单明了
    - 如果问题与<docs>里面的内容不相关，请回答 "根据内部知识库，找不到相关内容"，不需要额外补充内容
    </guidelines>

    Here are some documents for you to reference for your query.
    <docs>
    {context}
    </docs>"""

    for query in user_queries:
        print()
        print("==" * 50)

        default_llm_config = {
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'model_kwargs': {
                'temperature': 0.5,
                'max_tokens': 4096
            }
        }
        chatbot_config = {
            "chatbot_mode": mode,
            "use_history": query['use_history'],
            "default_llm_config": default_llm_config,
            "default_index_names": {
                "qq_match": ['admin-qq-bigo_qq'],
                "private_knowledge": ['admin-qd-bigo_qd'],
            },
            "private_knowledge_config": {
                "llm_config":{
                    "system_prompt": test_rag_system_prompt,
                }
            },
            "agent_config": {
                "only_use_rag_tool": True
            }
        }

        generate_answer(
            query['query'],
            stream=True,
            session_id=session_id,
            chatbot_config=chatbot_config,
            entry_type="common",
        )
        print()


def sso_batch_test():
    import pandas as pd
    data_path = "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/sso_poc/Bedrock_KB_TEST - Sheet1.csv"
    data = pd.read_csv(data_path).fillna("").to_dict(orient="records")
    mode = "agent"
    default_llm_config = {
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'model_kwargs': {
                'temperature': 0.1,
                'max_tokens': 4096
            }
        }
    default_retriever_config =  {
        "private_knowledge": {
            "top_k":10,
            "query_key": "query",
            "context_num": 1,
            "using_whole_doc": False
        }
    }
    session_id = f"multiturn_test_{time.time()}"
    results = []
    for i,datum in enumerate(data):
        query = datum['Question']
        if not query:
            continue
        print("="*25 + f"{i+1}.{query}" + "="*25)
        # session_id = f"multiturn_test_{time.time()}"
        chatbot_config = {
            "chatbot_mode": mode,
            "use_history": False,
            "enable_trace": True,
            "default_llm_config": default_llm_config,
            "default_retriever_config":default_retriever_config,
            "chatbot_id": "pr_test",
            "group_name": 'pr_test',
            "default_index_names": {
                "private_knowledge": ['pr_test-qd-sso_poc']
            },
            "agent_config": {
                "only_use_rag_tool": True
            }
        }
        
        r = generate_answer(
            query,
            stream=False,
            session_id=session_id,
            chatbot_config=chatbot_config,
            entry_type="common",
        )
        print(r)
        results.append({
            "query":query,
            "answer": r['message']['content']
        })
    
    print()
    print()
    for i,result in enumerate(results):
        print("="*50)
        print(f"question {i+1}: {result['query']}\nAnswer: {result['answer']}")
        

def anta_test():
    mode="agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"怎么进行个体户注册", "use_history":True},
    ]

    for query in user_queries:
        print()
        print("=="*50)

        default_llm_config = {
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'model_kwargs': {
                'temperature': 0.5, 'max_tokens': 4096}
            }
        chatbot_config = {
            "chatbot_mode": mode,
            "scene": "retail",
            "goods_id": 766158164989,
            "use_history": query['use_history'],
            "default_llm_config": default_llm_config,
            "default_index_names":{
                "qq_match":['bingo_qq'],
                "private_knowledge":[],
                "intention":['retail-intent']
            },
            "agent_config": {
                "only_use_rag_tool": True
            }
        }
        
        generate_answer(
            query['query'],
            stream=True,
            session_id=session_id,
            chatbot_config=chatbot_config,
            entry_type="retail",
        )
        print() 

if __name__ == "__main__":
    # complete_test_pr()
    # test_multi_turns_rag_pr()
    test_multi_turns_agent_pr()
    # test_qq_case_from_hanxu()
    # test_multi_turns_chat_pr()
    # bigo_test()
    # sso_batch_test()
    # anta_test()
    # bigo_test()

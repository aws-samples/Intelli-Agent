from local_test_base import generate_answer
import copy
import time


def test(chatbot_mode="agent",
         session_id=None,
         query=None,
         use_history=True,
         only_use_rag_tool=False):
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
             only_use_rag_tool=True)
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
            "use_history": True
        },
        {
            "query": "你好",
            "use_history": True
        },
        {
            "query": "人工客服",
            "use_history": True
        },
        {
            "query": "垃圾",
            "use_history": True
        },
        {
            "query": "什么是aws ec2",
            "use_history": True
        },
        {
            "query": "今天天气怎么样",
            "use_history": True
        },
        {
            "query": "我在上海",
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
             use_history=query['use_history'],
             only_use_rag_tool=True)
        print()


def complete_test_pr():
    print("start test in rag mode")
    test_multi_turns_rag_pr()
    print("finish test in rag mode")
    print("start test in agent mode")
    test_multi_turns_agent_pr()
    print("finish test in agent mode")

    print("start test in chat mode")
    test_multi_turns_chat_pr()
    # print(srg)
    print("finish test in chat mode")


def bigo_test():
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "怎么进行个体户注册",
            "use_history": True
        },
    ]

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
                "intention": ['default-intent'],
                "qq_match": ['bingo_qq'],
                "private_knowledge": ['wrong']
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
    results = []
    for i,datum in enumerate(data):
        query = datum['Question']
        if not query:
            continue
        print("="*25 + f"{i+1}.{query}" + "="*25)
        session_id = f"multiturn_test_{time.time()}"
        chatbot_config = {
            "chatbot_mode": mode,
            "use_history": False,
            "default_llm_config": default_llm_config,
            "default_index_names": {
                # "intention": ['default-intent'],
                # "qq_match": ['bingo_qq'],
                "private_knowledge": ['sso_poc']
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
                "private_knowledge":['wrong'],
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

def elec_test():
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "怎么进行个体户注册",
            "use_history": True
        },
    ]

    for query in user_queries:
        print()
        print("==" * 50)

        default_llm_config = {
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'model_kwargs': {
                'temperature': 0.5,
                'max_tokens': 4096,
            },
        }
        chatbot_config = {
            "chatbot_mode": mode,
            "use_history": query['use_history'],
            "default_llm_config": default_llm_config,
            "default_index_names": {
                "intention": ['default-intent'],
                "qq_match": ['bingo_qq'],
                "private_knowledge": ['ai-solar']
            },
            "agent_config": {
                "only_use_rag_tool": True
            },
           "private_knowledge_config": {
                "llm_config": {
                    **copy.deepcopy(default_llm_config),
                    'system_prompt': """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
                                    <guidelines>
                                    - NERVER say "根据搜索结果/大家好/谢谢...".
                                    - Output the context id which you refer to in the response in the <reference> tag.
                                    - Output the answer in the <answer> tag.
                                    </guidelines>

                                    Here are some documents for you to reference for your query.
                                    <docs>
                                    {context}
                                    </docs>"""
                },
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

if __name__ == "__main__":
    # complete_test_pr()
    # test_multi_turns_rag_pr()
    # test_multi_turns_agent_pr()
    # test_multi_turns_chat_pr()
    # bigo_test()
    # sso_batch_test()
    # anta_test()
    # bigo_test()
    elec_test()

from local_test_base import generate_answer
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


def sso_test():
    mode = "agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {
            "query": "怎么进行个体户注册",
            "use_history": True
        },
    ]



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
                "intention":['retail-intention']
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
    # test_multi_turns_agent_pr()
    # test_multi_turns_chat_pr()
    # anta_test()
    bigo_test()
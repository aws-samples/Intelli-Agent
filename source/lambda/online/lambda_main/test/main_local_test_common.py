from local_test_base import generate_answer
import time 

def test(chatbot_mode="agent",session_id=None,query=None,use_history=True):
    default_llm_config = {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'model_kwargs': {
            'temperature': 0.5, 'max_tokens': 4096}
        }
    chatbot_config = {
        "chatbot_mode": chatbot_mode,
        "use_history": use_history,
        "default_llm_config": default_llm_config,
    }
        # "default_workspace_config":{
        #     "intent_workspace_ids":["default-intent-debug"],
        # },
    
    generate_answer(
        query,
        stream=True,
        session_id=session_id,
        chatbot_config=chatbot_config,
        entry_type="common",
    )

def test_multi_turns_rag_pr():
    print("complete test for rag")
    print("++"*50)
    mode="rag"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"什么是aws ec2", "use_history":True},
        {"query":"什么是sagemaker", "use_history":True},
    ]

    for query in user_queries:
        print()
        print("=="*50)
        if isinstance(query,str):
            query = {"query":query}
        test(
            chatbot_mode=mode,
            session_id=session_id,
            query=query['query'],
            use_history=query['use_history']
        )
        print()

def test_multi_turns_chat_pr():
    print("complete test for chat")
    print("++"*50)
    mode="chat"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"今天几号", "use_history":True},
        {"query":"你好", "use_history":True},
        {"query":"你今天心情如何", "use_history":True},
    ]

    for query in user_queries:
        print()
        print("=="*50)
        if isinstance(query,str):
            query = {"query":query}
        test(
            chatbot_mode=mode,
            session_id=session_id,
            query=query['query'],
            use_history=query['use_history']
        )
        print()

def test_multi_turns_agent_pr():
    print("complete test for agent")
    print("++"*50)
    mode="agent"
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"什么是s3", "use_history":True},
        {"query":"你好", "use_history":True},
        {"query":"人工客服", "use_history":True},
        {"query":"垃圾", "use_history":True},
        {"query":"什么是aws ec2", "use_history":True},
        {"query":"今天天气怎么样", "use_history":True},
        {"query":"我在上海", "use_history":True},
    ]

    for query in user_queries:
        print()
        print("=="*50)
        if isinstance(query,str):
            query = {"query":query}
        test(
            chatbot_mode=mode,
            session_id=session_id,
            query=query['query'],
            use_history=query['use_history']
        )
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
  
if __name__ == "__main__":
    complete_test_pr()
    # test_multi_turns_agent_pr()
    # test_multi_turns_chat_pr()
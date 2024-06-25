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
        "default_llm_config": default_llm_config
    }
    
    generate_answer(
        query,
        stream=True,
        session_id=session_id,
        chatbot_config=chatbot_config,
        entry_type="common",
    )

def test_multi_turns_pr(mode="agent"):
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"今天天气怎么样", "use_history":True},
        {"query":"I am in Shanghai", "use_history":True},
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

def complete_test():
    print("start test in chat mode")
    test_multi_turns_pr("chat")
    print(srg)
    print("finish test in chat mode")
    print("start test in rag mode")
    test_multi_turns_pr("rag")
    print("finish test in rag mode")
    print("start test in agent mode")
    test_multi_turns_pr("agent")
    print("finish test in agent mode")
  
if __name__ == "__main__":
    # complete test for PR
    complete_test()
    

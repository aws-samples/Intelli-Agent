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

def test_multi_turns():
    session_id = f"multiturn_test_{time.time()}"
    user_queries = [
        {"query":"今天星期几？", "use_history":True},
        {"query":"今天星期三", "use_history":True},
        {"query":"今天星期几", "use_history":False},
        {"query":"我们进行了几轮对话", "use_history":True},
    ]

    for query in user_queries:
        print()
        print("=="*50)
        if isinstance(query,str):
            query = {"query":query}
        test(
            chatbot_mode='agent',
            session_id=session_id,
            query=query['query'],
            use_history=query['use_history']
        )
  
if __name__ == "__main__":
    # test(chatbot_mode="agent")
    test_multi_turns()
    

import requests 

# # atl 
# api_url = "https://9nb7vey1u7.execute-api.us-west-2.amazonaws.com/v1/llm"

# gamebi
api_url = "https://3yi34jorlg.execute-api.us-west-2.amazonaws.com/v1/llm"
llm_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
# endpoint_name = 'instruct-internlm2-chat-7b-f7dc2'
# model_id = "internlm2-chat-7b"

prompt = "How many player had done relive?"
r = requests.post(
    api_url,
    json={
        "type": "text2sql",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        # "temperature": 0.7,
        "llm_model_id":llm_model_id,
        "get_contexts" : False,
        # "enable_q_q_match":True
        # "retriever_config":{
        #     "retriever_top_k": 20,
        #     "chunk_num": 2,
        #     "using_whole_doc": False,
        #     "reranker_top_k": 10,
        #     "enable_reranker": True
        #     },
        # "generator_llm_config":{
        #     "model_kwargs":{
        #         "max_new_tokens": 2000,
        #         "temperature": 0.1,
        #         "top_p": 0.9
        #     },
        #     "model_id": model_id,
        #     "endpoint_name": endpoint_name,
        #     "context_num": 1
        # },
        # "query_process_config":{
        #     "conversation_query_rewrite_config":{
        #         "model_id":model_id,
        #         "endpoint_name":endpoint_name
        #     },
        #     "translate_config":{
        #         "model_id":model_id,
        #         "endpoint_name": endpoint_name
        #     }
        # },
        # "intent_config": { 
        #     "model_id": model_id,
        #     "endpoint_name": endpoint_name
        # },
        }
    )

print(r.status_code)
print(r.json())
# contexts = r.json()['contexts']
print(f"generate ans:")
print(f"{r.json()['choices'][0]['message']['content']}")
# print(f"{r.json()['choice'][['content']}")
# print(type(contexts))


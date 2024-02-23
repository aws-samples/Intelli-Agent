
import requests 
api_url = "https://9nb7vey1u7.execute-api.us-west-2.amazonaws.com/v1/"
           
llm_model_id = "anthropic.claude-v2:1" #"csdc-internlm-7b" # "anthropic.claude-v2:1"


prompt = "如何在不使用Red Hat共享的AMI的情况下将按需RHEL实例转换为BYOL，而不用重新部署每台RHEL服务器？"
r = requests.post(
    api_url,
    json={
        "model": "knowledge_qa",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "llm_model_id":llm_model_id,
        "get_contexts" : True,
        "enable_q_q_match":True
        }
    )

print(r.status_code)
print(r.json())
contexts = r.json()['contexts']
print(type(contexts))

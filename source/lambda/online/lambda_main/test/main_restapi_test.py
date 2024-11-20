
import requests

api_url = "https://vuvfkn2zr8.execute-api.us-west-2.amazonaws.com/v1/llmv2"

body = {
    "query": "What is lihoyo's most famous game???",
    "entry_type": "common",
    "session_id": "session_id",
    "chatbot_config": {
        "agent_config": {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "model_kwargs": {"temperature": 0.0, "max_tokens": 4096},
            "tools": [{"name": "give_final_response"}, {"name": "search_lihoyo"}]
        },
    }
}


r = requests.post(
    api_url,
    json=body
)

print(r.status_code)
print(r.json())

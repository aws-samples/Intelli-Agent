import os
import dotenv
import sys 
dotenv.load_dotenv()
sys.path.extend([".",'layer_logic'])

from common_utils.lambda_invoke_utils import invoke_lambda


def test(lambda_invoke_mode="local"):
    event_body = {
        "query": "hi",
        "chatbot_config":{
            "intention_config":{
                "retrievers": [
                        {
                            "type": "qq",
                            "workspace_ids": ["yb_intent"],
                            "config": {
                                "top_k": 10,
                            }
                        },
                    ]
            } 
        }
    }
    r = invoke_lambda(
        lambda_invoke_mode=lambda_invoke_mode,
        lambda_module_path='lambda_intention_detection.intention',
        lambda_name="Online_Intention_Detection",
        handler_name="lambda_handler",
        event_body=event_body
        )
    print(r)

if __name__ == "__main__":
    test(lambda_invoke_mode='local')
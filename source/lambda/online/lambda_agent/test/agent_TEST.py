import os
import sys
sys.path.append(".")
import dotenv
dotenv.load_dotenv()
import sys
os.environ['LAMBDA_INVOKE_MODE'] = 'local'

from layer_logic.utils.lambda_invoke_utils import invoke_lambda
from langchain_core.messages import HumanMessage,AIMessage

def test_local():
    event_body = {
        "chatbot_config":{
            "agent_config":{
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "tools":[{
                            "name": "get_weather",
                            "description": "Get the current weather in a given location",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                "location": {
                                    "description": "The city and state, e.g. San Francisco, CA",
                                    "type": "string"
                                },
                                "unit": {
                                    "description": "The unit of temperature",
                                    "allOf": [
                                    {
                                        "title": "Unit",
                                        "description": "An enumeration.",
                                        "enum": [
                                        "celsius",
                                        "fahrenheit"
                                        ]
                                    }
                                    ]
                                }
                                },
                                "required": [
                                "location",
                                "unit"
                                ]
                            }
                        }]
            }
        },
        "chat_history":[],
        "query":"What is the weather like in Beijing?"
    }
    
    ret = invoke_lambda(
        event_body=event_body,
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    print(ret)


if __name__ == "__main__":
    test_local()
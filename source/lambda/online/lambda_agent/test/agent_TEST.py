import os
import sys
import dotenv
dotenv.load_dotenv()
import sys
# os.environ['LAMBDA_INVOKE_MODE'] = 'local'
sys.path.extend([".",'layer_logic'])

from common_utils.lambda_invoke_utils import invoke_lambda


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
        "query":"What is the weather like in Beijing? I would like the temprature unit as Celsius"
    }
    
    ret = invoke_lambda(
        lambda_invoke_mode='local',
        event_body=event_body,
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    print(ret)


def test_lambda():
    event_body = {
        "chatbot_config":{
            "agent_config":{
                "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
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
        "query":"What is the weather like in Beijing? I would like the temprature unit as Celsius"
    }
    
    ret = invoke_lambda(
        lambda_invoke_mode='lambda',
        lambda_name="Online_Agent",
        event_body=event_body,
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    print(ret)

if __name__ == "__main__":
    # test_local()
    test_lambda()
import os
import sys
import dotenv
dotenv.load_dotenv()
import sys
# os.environ['LAMBDA_INVOKE_MODE'] = 'local'
sys.path.extend([".",'layer_logic'])

from common_utils.lambda_invoke_utils import invoke_lambda
from functions.tools import get_tool_by_name

# get_weather_tool_def = get_tool_by_name("get_weather").tool_def
# give_rhetorical_question = get_tool_by_name('give_rhetorical_question').tool_def
# give_final_response = get_tool_by_name('give_final_response').tool_def


def test_local():
    event_body = {
        "chatbot_config":{
            "agent_config":{
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "tools":[{"name":"get_weather"},{"name":"give_rhetorical_question"},{"name":"give_final_response"}]
            }
        },
        "chat_history":[],
        # "query":"What is the weather like in Beijing? I would like the temprature unit as Celsius"
        # "query":"What is the weather like in Beijing?"
        # "query":"今天天气怎么样？"
        # "query":"你好"
        "query":"你是名字是？"
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
                "tools":[{"name":"get_weather"},{"name":"give_rhetorical_question"},{"name":"give_final_response"}]
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
    test_local()
    # test_lambda()
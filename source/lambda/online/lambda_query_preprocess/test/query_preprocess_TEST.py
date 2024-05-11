import os
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
            "query_process_config":{
                "conversation_query_rewrite_config":{
                    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "result_key": "query"
                }

            }
        },
        "chat_history":[
            HumanMessage(content="《夜曲》是谁的歌曲？"),
            AIMessage(content="周杰伦")
        ],
        "query":"《七里香》是他的歌曲吗？"
    }
    
    ret = invoke_lambda(
        event_body=event_body,
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler"
    )
    print(ret)


if __name__ == "__main__":
    test_local()
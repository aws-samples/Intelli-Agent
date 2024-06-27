import sys
import dotenv
dotenv.load_dotenv()
# os.environ['LAMBDA_INVOKE_MODE'] = 'local'
sys.path.extend([".",'common_logic'])

from common_logic.common_utils.lambda_invoke_utils import invoke_lambda


def test_local():
    event_body = {
        "chatbot_config":{
            "query_process_config":{
                "conversation_query_rewrite_config":{
                    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
                }

            }
        },
        "chat_history":[
            {
                "role": "user",
                "content": "《夜曲》是谁的歌曲？"
            },
            {
                "role": "ai",
                "content": "周杰伦"
            }
        ],
        "query":"《七里香》是他的歌曲吗？"
    }
    
    ret = invoke_lambda(
        lambda_invoke_mode="local",
        event_body=event_body,
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler"
    )
    print(ret)


def test_lambda():
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
            {
                "role": "user",
                "content": "《夜曲》是谁的歌曲？"
            },
            {
                "role": "ai",
                "content": "周杰伦"
            }
        ],
        "query":"《七里香》是他的歌曲吗？"
    }
    
    ret = invoke_lambda(
        lambda_invoke_mode="lambda",
        event_body=event_body,
        lambda_name="Online_Query_Preprocess"
    )
    print(ret)


if __name__ == "__main__":
    test_local()
    # test_lambda()
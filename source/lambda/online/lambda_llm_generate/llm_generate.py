import json  
<<<<<<< HEAD
from utils.logger_utils  import get_logger
# from lambda_llm_generate.llm_generate_utils.llm_utils import LLMChain


logger = get_logger("llm_generate")

def lambda_handler(event, context=None):
    # event_body = json.loads(event["body"])
    # logger.info(f'config: {json.dumps(event_body,ensure_ascii=False,indent=2)}')
    # llm_chain_config = event_body['llm_config']
    # llm_chain_inputs = event_body['llm_input']
=======
from layer_logic.utils.logger_utils  import get_logger
from lambda_llm_generate.llm_generate_utils.llm_utils import LLMChain
from layer_logic.utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
from layer_logic.utils.serialization_utils import JSONEncoder

logger = get_logger("llm_generate")


@chatbot_lambda_call_wrapper
def lambda_handler(event_body, context=None):
    print(event_body)
    logger.info(f'config: {json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    llm_chain_config = event_body['llm_config']
    llm_chain_inputs = event_body['llm_input']
>>>>>>> 27289d7362c6309c35017ab03483d710a00b3e7a
    
    # chain = LLMChain.get_chain(
    #     **llm_chain_config
    # )
    # output = chain.invoke(llm_chain_inputs)

    event_body = event["body"]
    state:dict = event_body['state']

    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')


    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    state["answer"] = "finish llm generate test"
    response["body"] = {"state": state}

    return response


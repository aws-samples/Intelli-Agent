import json  
from utils.logger_utils  import get_logger
from llm_generate_utils.llm_utils import LLMChain


logger = get_logger("llm_generate")

def lambda_handler(event, context=None):
    event_body = json.loads(event["body"])
    logger.info(f'config: {json.dumps(event_body,ensure_ascii=False,indent=2)}')
    llm_chain_config = event_body['llm_config']
    llm_chain_inputs = event_body['llm_input']
    
    chain = LLMChain.get_chain(
        **llm_chain_config
    )
    output = chain.invoke(llm_chain_inputs)

    return output 


    


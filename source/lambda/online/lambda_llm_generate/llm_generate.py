from shared.utils.logger_utils import get_logger
from shared.langchain_integration.chains import LLMChain
from shared.utils.lambda_invoke_utils import chatbot_lambda_call_wrapper

logger = get_logger("llm_generate")


@chatbot_lambda_call_wrapper
def lambda_handler(event_body, context=None):
    llm_chain_config = event_body['llm_config']
    llm_chain_inputs = event_body['llm_input']

    chain = LLMChain.get_chain(
        **llm_chain_config
    )
    output = chain.invoke(llm_chain_inputs)

    return output

# knowledge base retrieve
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda

def knowledge_base_retrieve(event_body, context=None):
    chatbot_config = event_body['state']['chatbot_config']
    retriever_params = chatbot_config.get("rag_config",{}).get("retriever_config",{})
    retriever_params["query"] = event_body['kwargs']['query']
    # retriever_params = event_body['tool_init_kwargs']
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return contexts


def lambda_handler(event_body, context=None):
    contexts = knowledge_base_retrieve(event_body,context=context)
    return {"code":0, "result":"\n\n".join(contexts),"raw_results":contexts}



    






# knowledge base retrieve
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.constant import (
    LLMTaskType
)

def knowledge_base_retrieve(retriever_params, context=None):
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return contexts

def lambda_handler(event_body, context=None):
    state = event_body['state']
    retriever_params = state["chatbot_config"]["comparison_rag_config"]["retriever_config"]
    contexts = []
    retriever_params["query"] = event_body['kwargs']['query_a']
    contexts.extend(knowledge_base_retrieve(retriever_params, context=context))
    retriever_params["query"] = event_body['kwargs']['query_b']
    contexts.extend(knowledge_base_retrieve(retriever_params, context=context))
    context = "\n\n".join(contexts)

    # llm generate
    system_prompt = (f"请根据context内的信息回答问题:\n"
                    "<guidelines>\n"
                    " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
                    " - 使用中文回答。\n"
                    "</guidelines>\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>"
                )
    
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_daily_reception_config']['llm_config'], 
                "system_prompt": system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": {"query": state['query'], "chat_history": state['chat_history']}
            }
        )

    return {"code":0, "result":output}
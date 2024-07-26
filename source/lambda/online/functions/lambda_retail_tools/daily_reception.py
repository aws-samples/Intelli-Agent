# daily reception tool
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.common_utils.constant import (
    LLMTaskType
)

def lambda_handler(event_body,context=None):
    state = event_body['state']
    # retriver
    retriever_params = state["chatbot_config"]["rag_daily_reception_config"]['retriever_config']
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]
    context = "\n\n".join(contexts)
    send_trace(f'**rag_daily_reception_retriever** {context}')

    # llm generate
    system_prompt = (f"你是安踏的客服助理，正在帮用户解答问题，客户提出的问题大多是属于日常接待类别，你需要按照下面的guidelines进行回复:\n"
                    "<guidelines>\n"
                    " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
                    " - 使用中文回答。\n"
                    "</guidelines>\n"
                    "下面列举了一些具体的场景下的回复，你可以结合用户的问题进行参考:\n"
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
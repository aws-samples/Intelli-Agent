# promotion tool 

from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.common_utils.constant import (
    LLMTaskType
)


def lambda_handler(event_body,context=None):
    state = event_body['state']
    
    # retrieve
    retriever_params = state["chatbot_config"]["rag_promotion_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_promotion_retriever** {context}', state["stream"], state["ws_connection_id"])

    # llm generate
    system_prompt = ("你是安踏的客服助理，正在帮消费者解答有关于商品促销的问题，这些问题是有关于积分、奖品、奖励等方面。\n"
                     "context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                    f"<context>\n{context}\n</context>\n"
                    "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 如果问题与context内容不相关，就不要采用。\n"
                    " - 使用中文进行回答。\n"
                    "</guidelines>"
    )
   
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_promotion_config']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    
    return {"code":0, "result": output}


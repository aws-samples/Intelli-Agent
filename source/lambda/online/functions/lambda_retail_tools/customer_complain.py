# customer complain
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.common_utils.constant import (
    LLMTaskType
)


def lambda_handler(event_body,context=None):
    state = event_body['state']
    # call retriever
    retriever_params = state["chatbot_config"]["rag_customer_complain_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_customer_complain_retriever** {context}', state["stream"], state["ws_connection_id"])
    
    # llm generate
    # prompt = dedent(f"""你是安踏的客服助理，正在处理有关于客户抱怨的问题，这些问题有关于商品质量等方面，需要你按照下面的guidelines进行回复:
    system_prompt = ("你是安踏的客服助理，正在处理有关于消费者抱怨的问题。context列举了一些可能和客户问题有关的具体场景及回复，你可以进行参考:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                    "需要你按照下面的guidelines进行回复:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 尽量安抚客户情绪。\n"
                    " - 直接回答，不要说\"亲爱的顾客，您好\"\n"
                    "</guidelines>\n"
                    )
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_customer_complain_config']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    
    return {"code":0, "result":output}
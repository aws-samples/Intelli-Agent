# rule_url_reply
import random 
import re  
from functions.lambda_retail_tools.product_information_search import goods_dict
from common_logic.common_utils.constant import LLMTaskType
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda


def lambda_handler(event_body, context=None):
    state = event_body["state"]
    state["extra_response"]["current_agent_intent_type"] = "rule reply"
    goods_info_tag = state['goods_info_tag']
    if state['query'].endswith(('.jpg','.png')):
        answer = random.choice([
            "收到，亲。请问我们可以怎么为您效劳呢？",
            "您好，请问有什么需要帮助的吗？"
        ])
        return {"code":0, "result": answer}
    # product information
    r = re.findall(r"item.htm\?id=(.*)",state['query'])
    if r:
        goods_id = r[0]
    else:
        goods_id = 0
    if goods_id in goods_dict:
        # call llm to make summary of goods info
        human_goods_info = state['human_goods_info']
        output = f"您好，该商品的特点是:\n{human_goods_info}"
        if human_goods_info:
            system_prompt = (f"你是安踏的客服助理，当前用户对下面的商品感兴趣:\n"
                        f"<{goods_info_tag}>\n{human_goods_info}\n</{goods_info_tag}>\n"
                        "请你结合商品的基础信息，特别是卖点信息返回一句推荐语。"
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
    
    return {"code":0, "result":"您好"}
# goods after sales
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.common_utils.constant import (
    LLMTaskType
)
from datetime import datetime 


def lambda_handler(event_body,context=None):
    state = event_body['state']
    recent_tool_calling:list[dict] = state['function_calling_parsed_tool_calls'][0]
    if "shop" in recent_tool_calling['kwargs'] and recent_tool_calling['kwargs']['shop'] != "tianmao":
        contexts = ["顾客不是在天猫购买的商品，请他咨询其他商家"]
        # return {"contexts": contexts}
    else:
        retriever_params = state["chatbot_config"]["rag_product_aftersales_config"]["retriever_config"]
        retriever_params["query"] = state["query"]
        output:str = invoke_lambda(
            event_body=retriever_params,
            lambda_name="Online_Functions",
            lambda_module_path="functions.functions_utils.retriever.retriever",
            handler_name="lambda_handler"
        )
        contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_product_aftersales_retriever** {context}', state["stream"], state["ws_connection_id"])
    

    # llm generate 
    create_time = state.get('create_time', None)
    goods_id = state.get('chatbot_config').get('goods_id', 757492962957)
    try:
        create_datetime_object = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S.%f')
    except Exception as e:
        create_datetime_object = datetime.now()
        print(f"create_time: {create_time} is not valid, use current time instead.")
    create_time_str = create_datetime_object.strftime('%Y-%m-%d')
    # TODO: fix received time format

    from lambda_main.main_utils.online_entries.retail_entry import order_dict
    
    received_time = order_dict.get(str(goods_id), {}).get("received_time", "2023/9/129:03:13")
    order_time = " ".join([received_time[:9], received_time[9:]])
    try:
        order_date_str = datetime.strptime(order_time, '%Y/%m/%d %H:%M:%S').strftime('%Y-%m-%d')
        receive_elapsed_days = (create_datetime_object - datetime.strptime(order_date_str, '%Y-%m-%d')).days
        receive_elapsed_months = receive_elapsed_days // 30
    except Exception as e:
        order_date_str = "2023-9-12"
        receive_elapsed_months = 6

    system_prompt = (f"你是安踏的客服助理，正在帮消费者解答问题，消费者提出的问题大多是属于商品的质量和物流规则。context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                    f"客户咨询的问题所对应的订单日期为{order_date_str}。\n"
                    f"当前时间{create_time_str}\n"
                    f"客户收到商品已经超过{receive_elapsed_months}个月\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                    "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 如果问题与context内容不相关，就不要采用。\n"
                    " - 消费者的问题里面可能包含口语化的表达，比如鞋子开胶的意思是用胶黏合的鞋体裂开。这和胶丝遗留没有关系\n"
                    " - 洗涤后出现问题也属于质量问题\n"
                    " - 消费者的回复不够清晰的时候，直接回复: 不知道刚才给您的建议是否有帮助？。不要有额外补充\n"
                    " - 如果客户问到质量相关问题，请根据前面的订单信息和三包规则，确定是否超出三包期限，如果超出三包期限请告知消费者无法处理，如果在三包期限内请按照三包要求处理，并安抚。\n"
                    "</guidelines>\n"
                    )
    # print('llm config',state['chatbot_config']['rag_product_aftersales_config']['llm_config'])
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_product_aftersales_config']['llm_config'], 
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT
            },
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    
    return {"code":0, "result":output}
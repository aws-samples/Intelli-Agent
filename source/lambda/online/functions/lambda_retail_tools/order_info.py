import os
import re
import boto3
import json

from common_logic.common_utils.s3_utils import download_file_from_s3,check_local_folder
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda

order_info_path = "/tmp/functions/retail_tools/lambda_order_info/order_info.json"
check_local_folder(order_info_path)
download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/order_info.json", order_info_path)
order_dict = json.load(open(order_info_path))

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = state["chatbot_config"]["goods_id"]
#     ans = """
#     如果遇到是关于是关于发货的问题，请回答‘根据您的问题,FILA实施全国多仓发货,下单后正常会48小时内帮您安排发货的哦。如果超过48小时还未发货,您可以随时联系我们客服,我们会尽快为您解决。’
# """
    result = order_dict.get(goods_id, {}).get("status","") 
    
    if result == "":
        search_result = 0
        retriever_params = state["chatbot_config"]["rag_delivery_track_config"]["retriever_config"]
        retriever_params["query"] = state["query"]
        output:str = invoke_lambda(
            event_body=retriever_params,
            lambda_name="Online_Functions",
            lambda_module_path="functions.functions_utils.retriever.retriever",
            handler_name="lambda_handler"
        )
        contexts = [doc['page_content'] for doc in output['result']['docs']]

        result = "\n\n".join(contexts)

        # search_result = f"当前没有查询到相关内容，请参考下面的内容，用一句话进行简洁回复:\n<内容>\n{result}\n</内容>"
        # result = search_result
        # result = contexts
    else:
        search_result = 1

    return {"code":0, "result":result, "name": "product_information_search", "search_result": search_result}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
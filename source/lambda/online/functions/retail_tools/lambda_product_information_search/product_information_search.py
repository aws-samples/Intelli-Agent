import json
import os
from common_logic.common_utils.s3_utils import download_file_from_s3
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,node_monitor_wrapper
from common_logic.common_utils.lambda_invoke_utils import send_trace,is_running_local

goods_info_path = "/tmp/functions/retail_tools/lambda_order_info/goods_info.json"
parent_path = '/'.join((goods_info_path).split('/')[:-1])
os.system(f"mkdir -p {parent_path}")

download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/goods_info.json", goods_info_path)
goods_dict = json.load(open(goods_info_path))

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = str(state["chatbot_config"]["goods_id"])
    context_goods_info = goods_dict[goods_id]

    retriever_params = state["chatbot_config"]["rag_goods_info_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    goods_info_list = [doc['page_content'] for doc in output['result']['docs']]

    query_goods_info = "\n\n".join(goods_info_list)
    send_trace(f'**rag_goods_info_retriever** {context}', state["stream"], state["ws_connection_id"])
    result = f"**用户当前咨询的商品是** {context_goods_info}\n\n**用户可能想找的商品是** {query_goods_info}"

    return {"code":0, "result":result, "name": "product_information_search"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
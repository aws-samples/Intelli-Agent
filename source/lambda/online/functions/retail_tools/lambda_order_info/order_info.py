import os
import re
import boto3
import json

from common_logic.common_utils.s3_utils import download_file_from_s3,check_local_folder

order_info_path = "/tmp/functions/retail_tools/lambda_order_info/order_info.json"
check_local_folder(order_info_path)
download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/order_info.json", order_info_path)
order_dict = json.load(open(order_info_path))

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = state["chatbot_config"]["goods_id"]
    result = order_dict.get(goods_id, {}).get("status", "卖家已发货")
    return {"code":0, "result":result, "name": "product_information_search"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
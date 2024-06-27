import json
import os
from common_logic.common_utils.s3_utils import download_file_from_s3

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
    result = goods_dict[goods_id]
    return {"code":0, "result":result, "name": "product_information_search"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
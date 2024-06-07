import os
import re
import math
import boto3
import pandas as pd
from common_utils.s3_utils import download_dir_from_s3

def download_dir_from_s3(bucket_name, s3_dir_path, local_dir_path):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    for result in paginator.paginate(Bucket=bucket_name, Prefix=s3_dir_path):
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local_dir_path + os.sep + file.get('Key'))):
                    os.makedirs(os.path.dirname(local_dir_path + os.sep + file.get('Key')))
                s3.download_file(bucket_name, file.get('Key'), local_dir_path + os.sep + file.get('Key'))

def get_order_dict(data_file_path):
    order_dict = {} 
    order_df = pd.read_excel(data_file_path, "订单号")
    for index, row in order_df.iterrows():
        order_id = row["消费者原生"]
        if type(order_id) != str:
            continue
        order_id = re.match(r"订单号:(\d+).*", str(order_id)).group(1)
        if order_id not in order_dict:
            order_dict[order_id] = {}
        order_dict[order_id]["status"] = row["订单状态"]
        order_dict[order_id]["received_time"] = row["签收时间"]
        if "goods_list" not in order_dict[order_id]:
            order_dict[order_id]["goods_list"] = []
        order_dict[order_id]["goods_list"].append(row["订单ID"])
    return order_dict

download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "/tmp/functions/retail_tools/lambda_order_info/")
order_dict = get_order_dict("/tmp/functions/retail_tools/lambda_order_info/retail/detail/TB0327.xlsx")


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
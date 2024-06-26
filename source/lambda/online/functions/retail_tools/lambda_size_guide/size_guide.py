import os
import re
import json

import numpy as np

from common_logic.common_utils.s3_utils import download_file_from_s3

good2type_dict_path = "/tmp/functions/retail_tools/lambda_size_guide/good2type_dict.json"
size_dict_path = "/tmp/functions/retail_tools/lambda_size_guide/size_dict.json"
download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/good2type_dict.json", good2type_dict_path)
download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/size_dict.json", size_dict_path)
good2type_dict = json.load(open(good2type_dict_path))
size_dict = json.load(open(size_dict_path))

def find_nearest(array, value):
    float_array = np.asarray([float(x) for x in array])
    array = np.asarray(array)
    idx = (np.abs(float_array - value)).argmin()
    return array[idx]

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = str(state["chatbot_config"]["goods_id"])
    kwargs = event_body["kwargs"]
    if goods_id not in good2type_dict:
        return {"code":1, "result":"goods_id is invalid"}
    goods_type_1, goods_type_2 = good2type_dict[goods_id]
    if goods_type_1 == "shoes":
        if "shoes_size" in kwargs:
            shoe_size = float(kwargs["shoes_size"])
            std_shoe_size = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").keys()), shoe_size)
            result = size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").get(std_shoe_size, "42")
        elif "foot_length" in kwargs:
            foot_length = float(kwargs["foot_length"])
            std_foot_length = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("foot_length").keys()), foot_length)
            result = size_dict.get(goods_type_1).get(goods_type_2).get("foot_length").get(std_foot_length, "28")
        else:
            return {"code":1, "result":"shoes size or foot length is required"}
    elif goods_type_1 == "apparel":
        if "height" not in kwargs:
            return {"code":1, "result":"height is required"}
        if "weight" not in kwargs:
            return {"code":1, "result":"weight is required"}
        height = float(kwargs["height"])
        std_height = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").keys()), height)
        weight = float(kwargs["weight"])
        std_weight = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").get(std_height).keys()), weight)
        result = size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").get(std_height).get(std_weight)
    return {"code":0, "result":result, "name": "尺码查询"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
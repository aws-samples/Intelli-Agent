import os
import re
import json

import numpy as np

from common_logic.common_utils.s3_utils import download_file_from_s3, check_local_folder

good2type_dict_path = "/tmp/functions/retail_tools/lambda_size_guide/good2type_dict.json"
size_dict_path = "/tmp/functions/retail_tools/lambda_size_guide/size_dict.json"
check_local_folder(good2type_dict_path)
check_local_folder(size_dict_path)
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
        return {"code":1, "result":"该商品的尺码信息缺失，请不要使用尺码工具"}
    goods_type_1, goods_type_2 = good2type_dict[goods_id]
    if goods_type_1 == "shoes":
        if "shoes_size" in kwargs:
            try:
                shoe_size = float(kwargs["shoes_size"])
            except:
                return {"code":1, "result":"shoes_size should be a number"}
            if goods_type_1 == "shoes" and goods_type_2 == "童鞋":
                return {"code":1, "result":"童鞋不存在鞋码，请输入脚长查询"}
            std_shoe_size = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").keys()), shoe_size)
            result = size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").get(std_shoe_size, "42")
            # No sutabale size for the input shoes size or foot length
            if result == "此款暂无适合亲的尺码":
                result += "，您当前输入的鞋码为{}，请确认一下参数是否正确，如果有修改可以再次调用尺码工具".format(shoe_size)
        elif "foot_length" in kwargs:
            try:
                foot_length = float(kwargs["foot_length"])
            except:
                return {"code":1, "result":"foot_length should be a number"}
            std_foot_length = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("foot_length").keys()), foot_length)
            result = size_dict.get(goods_type_1).get(goods_type_2).get("foot_length").get(std_foot_length, "28")
            # No sutabale size for the input foot length
            if result == "此款暂无适合亲的尺码":
                result += "，您当前输入的脚长为{}cm，请确认一下参数是否正确，如果有修改可以再次调用尺码工具".format(foot_length)
        else:
            return {"code":1, "result":"请继续询问用户的脚长或鞋码"}
    elif goods_type_1 == "apparel":
        if "height" not in kwargs:
            return {"code":1, "result":"请继续询问用户的身高"}
        if "weight" not in kwargs:
            return {"code":1, "result":"请继续询问用户的体重"}
        try:
            height = float(kwargs["height"])
            weight = float(kwargs["weight"])
        except:
            return {"code":1, "result":"height and weight should be numbers"}
        std_height = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").keys()), height)
        std_weight = find_nearest(list(size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").get(std_height).keys()), weight)
        result = size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").get(std_height).get(std_weight)
        # No sutabale size for the input height and weight
        if result == "亲亲，很抱歉，这款暂时没有适合您的尺码":
            result += "，您当前输入的身高为{}cm，体重为{}kg，请确认一下参数是否正确，如果有修改可以再次调用尺码工具".format(height, weight)
    return {"code":0, "result":result, "name": "尺码查询"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
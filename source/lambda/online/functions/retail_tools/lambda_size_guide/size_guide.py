import os
import re
import pandas as pd

from common_utils.s3_utils import download_dir_from_s3

def get_goods_type_1(file_name):
    if "鞋" in file_name:
        goods_type_1 = "shoes"
    else:
        goods_type_1 = "apparel"
    return goods_type_1

def get_goods_type_2(file_name):
    return file_name.split(".")[0].split("-")[0]

def get_goods_type_3(file_name):
    if "鞋" in file_name:
        if "鞋码" in file_name:
            goods_type_3 = "shoes_size"
        elif "脚长" in file_name:
            goods_type_3 = "foot_length"
    else:
        goods_type_3 = "height_weight"
    return goods_type_3

def get_size_dict():
    goods2type_dict = {}
    size_dict = {}
    # iterator all files in directory
    for root, dirs, files in os.walk("functions/retail_tools/lambda_size_guide/retail/size"):
        print(files)
        for file in files:
            goods_type_1 = get_goods_type_1(file)
            goods_type_2 = get_goods_type_2(file)
            # read file
            if file.endswith(".txt"):
                with open(os.path.join(root, file)) as f:
                    for line in f:
                        goods_id = line.strip()
                        goods2type_dict[goods_id] = (goods_type_1, goods_type_2)
            elif file.endswith(".xls"):
                if goods_type_1 not in size_dict:
                    size_dict[goods_type_1] = {}
                goods_type_2 = get_goods_type_2(file)
                if goods_type_2 not in size_dict[goods_type_1]:
                    size_dict[goods_type_1][goods_type_2] = {}
                goods_type_3 = get_goods_type_3(file)
                data_file_path = os.path.join(root, file)
                if goods_type_3 == "height_weight":
                    size_dict[goods_type_1][goods_type_2][goods_type_3] = get_apparel_size_dict(data_file_path)
                elif goods_type_3 == "shoes_size":
                    size_dict[goods_type_1][goods_type_2][goods_type_3] = get_shoes_size_dict(data_file_path)
                elif goods_type_3 == "foot_length":
                    size_dict[goods_type_1][goods_type_2][goods_type_3] = get_foot_length_dict(data_file_path)
    return goods2type_dict, size_dict

def get_apparel_size_dict(data_file_path):
    apparel_size_dict = {} 
    # size_info_df = pd.read_excel(open(data_file_path, encoding="utf-8-sig", errors="ignore"))
    size_info_df = pd.read_excel(data_file_path)
    # get row
    for index, row in size_info_df.iterrows():
        for key in row.keys():
            if key == "体重(kg) \\ 身高(cm)":
                weight_min, weight_max = row[key].split("-")
            elif re.match(r"\d+-\d+", key):
                height_min, height_max = key.split("-")
                for height in range(int(height_min), int(height_max)):
                    if height not in apparel_size_dict:
                        apparel_size_dict[height] = {}
                    for weight in range(int(weight_min), int(weight_max)):
                        apparel_size_dict[height][weight] = row[key]
    return apparel_size_dict

def get_shoes_size_dict(data_file_path):
    shoes_size_dict = {} 
    size_info_df = pd.read_excel(data_file_path)
    # get row
    for index, row in size_info_df.iterrows():
        for key in row.keys():
            if re.match(r"[\d\.]+-[\d\.]+", key):
                size_min, size_max = key.split("-")
                for size in range(int(float(size_min)*2), int(float(size_max)*2)):
                    size /= 2
                    if size not in shoes_size_dict:
                        shoes_size_dict[size] = row[key]
    return shoes_size_dict

def get_foot_length_dict(data_file_path):
    foot_length_dict = {}
    size_info_df = pd.read_excel(data_file_path)
    # get row
    for index, row in size_info_df.iterrows():
        for key in row.keys():
            if re.match(r"[\d\.]+-[\d\.]+", key):
                size_min, size_max = key.split("-")
                for size in range(int(float(size_min)*2), int(float(size_max)*2)):
                    size /= 2
                    if size not in foot_length_dict:
                        foot_length_dict[size] = row[key]
    return foot_length_dict 

download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "functions/retail_tools/lambda_size_guide/")
good2type_dict, size_dict = get_size_dict()

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = state["chatbot_config"]["goods_id"]
    kwargs = event_body["kwargs"]
    if goods_id not in good2type_dict:
        return {"code":1, "result":"goods_id is invalid"}
    goods_type_1, goods_type_2 = good2type_dict[goods_id]
    if goods_type_1 == "shoes":
        if "shoes_size" in kwargs:
            shoe_size = float(kwargs["shoes_size"])
            result = size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").get(shoe_size, "42")
        elif "foot_length" in kwargs:
            shoe_size = float(kwargs["foot_length"])
            result = size_dict.get(goods_type_1).get(goods_type_2).get("shoes_size").get(weight, "L")
        else:
            return {"code":1, "result":"shoes size or foot length is required"}
    elif goods_type_1 == "apparel":
        if "height" not in kwargs:
            return {"code":1, "result":"height is required"}
        if "weight" not in kwargs:
            return {"code":1, "result":"weight is required"}
        height = int(float(kwargs["height"]))
        weight = int(float(kwargs["weight"]))
        result = size_dict.get(goods_type_1).get(goods_type_2).get("height_weight").get(height).get(weight, "L")
    return {"code":0, "result":result, "name": "尺码查询"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
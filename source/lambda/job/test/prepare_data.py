import pandas as pd
import re
import json
import os

from common_logic.common_utils.s3_utils import download_dir_from_s3, upload_file_to_s3

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

def get_goods_dict_1(data_file_path):
    goods_dict = {}
    # size_info_df = pd.read_excel(open(data_file_path, encoding="utf-8-sig", errors="ignore"))
    goods_df = pd.read_excel(data_file_path, "商品信息登记").fillna("")
    # get row
    for index, row in goods_df.iterrows():
        goods_id = str(row["商品ID"])
        assert len(goods_id) == 12
        goods_info = json.dumps({"卖点（含材质属性）":row["卖点（含材质属性）"]},ensure_ascii=False)
        goods_url = row["商品链接"]
        goods_dict[goods_id] = {"goods_info": goods_info, "goods_url": goods_url}
    return goods_dict

def get_goods_dict_2(data_file_path):
    goods_dict = {}
    # size_info_df = pd.read_excel(open(data_file_path, encoding="utf-8-sig", errors="ignore"))
    goods_df_dict = pd.read_excel(data_file_path,None)
    # get row
    for goods_type, goods_df in goods_df_dict.items():
        goods_df = goods_df.fillna("")
        for index, row in goods_df.iterrows():
            if "商品ID" in row:
                goods_id = str(row["商品ID"])
                assert len(goods_id) == 12
                goods_info = json.dumps((row.to_dict()), ensure_ascii=False)
                goods_url = row["商品链接"]
                goods_dict[goods_id] = {"goods_info": goods_info, "goods_url": goods_url, "goods_type": goods_type}
    return goods_dict

def get_goods_dict_3(data_file_path):
    goods_dict = {}
    goods_df_dict = pd.read_excel(data_file_path,None)
    # get row
    for sheet_name, goods_df in goods_df_dict.items():
        goods_df = goods_df.fillna("")
        for index, row in goods_df.iterrows():
            if "plat_goods_id" in row:
                goods_id = str(row["plat_goods_id"])
                assert len(goods_id) == 12
                goods_info = json.dumps((row.to_dict()), ensure_ascii=False)
                goods_url = row["商品链接"]
                goods_dict[goods_id] = {"goods_info": goods_info, "goods_url": goods_url}
    return goods_dict

def combine_goods_dict(goods_dict_list):
    combined_goods_dict = {}
    for goods_dict in goods_dict_list:
        for goods_id, goods_value in goods_dict.items():
            if goods_id not in combined_goods_dict:
                combined_goods_dict[goods_id] = {}
            for key, value in goods_value.items():
                if key == "goods_info":
                    if key not in combined_goods_dict[goods_id]:
                        combined_goods_dict[goods_id][key] = value
                    else:
                        # TODO: combine goods_info
                        combined_goods_dict[goods_id][key] = value
                else:
                    combined_goods_dict[goods_id][key] = value
    return combined_goods_dict

def trans_goods_info_dict_to_jsonl(goods_info_dict, goods_info_jsonl_file_path):
    with open(goods_info_jsonl_file_path, "w") as f:
        for goods_id in goods_info_dict:
            goods_info_str = goods_info_dict[goods_id]["goods_info"]
            goods_url = goods_info_dict[goods_id]["goods_url"]
            goods_type = goods_info_dict[goods_id].get("goods_type", "")
            all_json_data = {
                "question": goods_info_str,
                "answer": {
                    "goods_url": goods_url,
                    "goods_info": goods_info_str,
                    "goods_id": goods_id,
                    "goods_type": goods_type
                }
            }
            f.write(json.dumps(all_json_data, ensure_ascii=False) + "\n")
            goods_info = json.loads(goods_info_str)
            for key in goods_info:
                if type(goods_info[key]) != str or len(goods_info[key]) <= 0:
                    continue
                json_data = {
                    "question": f"{key}: {goods_info[key]}",
                    "answer": {
                        "goods_url": goods_url,
                        "goods_info": goods_info_str,
                        "goods_id": goods_id,
                        "goods_type": goods_type
                    }
                }
                f.write(json.dumps(json_data, ensure_ascii=False) + "\n")

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
    for root, dirs, files in os.walk("/tmp/functions/retail_tools/lambda_size_guide/retail/size"):
        print(files)
        for file in files:
            goods_type_1 = get_goods_type_1(file)
            goods_type_2 = get_goods_type_2(file)
            # read file
            if file.endswith(".txt"):
                with open(os.path.join(root, file), encoding="utf-8-sig") as f:
                    for line in f:
                        goods_id = line.strip()
                        assert len(goods_id) == 12
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

def patch_good2type_dict(good2type_dict):
    good2type_dict["748090908717"] = ("apparel", "标准男装")
    return good2type_dict

# Get order information
# download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "/tmp/functions/retail_tools/lambda_order_info/")
# order_dict = get_order_dict("/tmp/functions/retail_tools/lambda_order_info/retail/detail/TB0327.xlsx")
# order_dict_json_file = "/tmp/functions/retail_tools/lambda_order_info/order_info.json"
# json.dump(order_dict, open(order_dict_json_file, "w"), ensure_ascii=False, indent=4)
# upload_file_to_s3("aws-chatbot-knowledge-base-test", "retail_json/order_info.json", order_dict_json_file)

# Get goods information
# download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "/tmp/functions/retail_tools/lambda_product_information_search/")
goods_dict = get_goods_dict_1("/tmp/functions/retail_tools/lambda_product_information_search/retail/detail/TB0327.xlsx")
goods_dict_2 = get_goods_dict_2("/tmp/functions/retail_tools/lambda_product_information_search/retail/detail/商品属性表.xlsx")
goods_dict_3 = get_goods_dict_3("/tmp/functions/retail_tools/lambda_product_information_search/retail/detail/天猫官旗-商品信息.xlsx")
combined_goods_dict = combine_goods_dict([goods_dict, goods_dict_2, goods_dict_3])
goods_dict_json_file = "/tmp/functions/retail_tools/lambda_product_information_search/goods_info.json"
json.dump(combined_goods_dict, open(goods_dict_json_file, "w"), ensure_ascii=False, indent=4)
upload_file_to_s3("aws-chatbot-knowledge-base-test", "retail_json/goods_info.json", goods_dict_json_file)
trans_goods_info_dict_to_jsonl(combined_goods_dict, "../job/poc/goods_data/detail/goods_info.jsonl")

# Get size information
# download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "/tmp/functions/retail_tools/lambda_size_guide/")
# good2type_dict, size_dict = get_size_dict()
# patch_good2type_dict(good2type_dict)
# good2type_dict_json_file = "/tmp/functions/retail_tools/lambda_size_guide/good2type_dict.json"
# size_dict_json_file = "/tmp/functions/retail_tools/lambda_size_guide/size_dict.json"
# json.dump(good2type_dict, open(good2type_dict_json_file, "w"), ensure_ascii=False, indent=4)
# json.dump(size_dict, open(size_dict_json_file, "w"), ensure_ascii=False, indent=4)
# upload_file_to_s3("aws-chatbot-knowledge-base-test", "retail_json/good2type_dict.json", good2type_dict_json_file)
# upload_file_to_s3("aws-chatbot-knowledge-base-test", "retail_json/size_dict.json", size_dict_json_file)
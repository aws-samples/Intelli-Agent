import os
import re
import pandas as pd

def get_size_dict():
    good2type_dict = {}
    size_dict = {}
    # iterator all files in directory
    for root, dirs, files in os.walk("functions/retail_tools/lambda_size/goods_data/size"):
        print(files)
        for file in files:
            # read file
            if file.endswith(".txt"):
                goods_type = file.split("-")[0]
                with open(os.path.join(root, file)) as f:
                    for line in f:
                        goods_id = line.strip()
                        good2type_dict[goods_id] = goods_type
            elif file.endswith(".xls") and "鞋" not in file:
                goods_type = file.split("-")[0]
                if goods_type not in size_dict:
                    size_dict[goods_type] = {}
                else:
                    size_dict[goods_type] = {}
                size_info_df = pd.read_excel(os.path.join(root, file))
                # get row
                for index, row in size_info_df.iterrows():
                    for key in row.keys():
                        if key == "体重(kg) \\ 身高(cm)":
                            weight_min, weight_max = row[key].split("-")
                        elif re.match(r"\d+-\d+", key):
                            height_min, height_max = key.split("-")
                            for height in range(int(height_min), int(height_max)):
                                if height not in size_dict[goods_type]:
                                    size_dict[goods_type][height] = {}
                                for weight in range(int(weight_min), int(weight_max)):
                                    size_dict[goods_type][height][weight] = row[key]
    return good2type_dict, size_dict

good2type_dict, size_dict = get_size_dict()

def lambda_handler(event_body, context=None):
    goods_id = event_body.get("goods_id", "637260524878")
    good_type = good2type_dict.get(goods_id, "标准男装")
    height = event_body.get("height", 175)
    weight = event_body.get("weight", 65)
    result = size_dict.get(good_type, {}).get(height, {}).get(weight, "L")
    return {"code":0, "result":result, "name": "尺码查询"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
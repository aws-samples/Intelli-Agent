import json
import pandas as pd

from common_utils.s3_utils import download_dir_from_s3

def get_goods_dict_1(data_file_path):
    goods_dict = {}
    # size_info_df = pd.read_excel(open(data_file_path, encoding="utf-8-sig", errors="ignore"))
    goods_df = pd.read_excel(data_file_path, "商品信息登记").fillna("")
    # get row
    for index, row in goods_df.iterrows():
        goods_id = row["商品ID"]
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
                goods_id = row["商品ID"]
                goods_info = json.dumps((row.to_dict()), ensure_ascii=False)
                goods_url = row["商品链接"]
                goods_dict[goods_id] = {"goods_info": goods_info, "goods_url": goods_url}
    return goods_dict

download_dir_from_s3("aws-chatbot-knowledge-base-test", "retail", "/tmp/functions/retail_tools/lambda_product_information_search/")
goods_dict = get_goods_dict_1("/tmp/functions/retail_tools/lambda_product_information_search/retail/detail/TB0327.xlsx")
goods_dict_2 = get_goods_dict_2("/tmp/functions/retail_tools/lambda_product_information_search/retail/detail/商品属性表.xlsx")
goods_dict.update(goods_dict_2)

def lambda_handler(event_body, context=None):
    state = event_body["state"]
    if "goods_id" not in state["chatbot_config"]:
        return {"code":1, "result":"goods_id is required"}
    goods_id = state["chatbot_config"]["goods_id"]
    result = goods_dict.get(int(goods_id), {"goods_info": "面料：合成革/织物/牛剖层皮革/橡塑材料 卖点：1、KM代表“公里”的意思，灵感来自70年代复古跑鞋款式，从富有艺术感的建筑堆叠元素中打造双层鞋底设计，体现别致、多样化的设计语言2、体验到双层外底、双鞋舌带来的奇妙穿着感受。3、本季携手英国“V&A博物馆”，再造艺术联名系波段产品;本次选取博物馆中，英国艺术家威廉·德·摩根在十九世纪创作的一系列的瓷砖&瓷器艺术品。",
                                            "goods_url": "https://item.taobao.com/item.htm?id=756104239829"})
    return {"code":0, "result":result, "name": "product_information_search"}

if __name__ == "__main__":
    event_body = {}
    lambda_handler(event_body)
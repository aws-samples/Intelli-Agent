import os
import sys
import boto3
from dotenv import load_dotenv

sys.path.append('../online')
sys.path.append('../etl')
import sfn_handler
from common_logic.common_utils import s3_utils

try:
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__),'../../online/lambda_main/test/.env')
    )
except:
    print("cannot find .env")

# run multiple process ingestion

dynamodb = boto3.resource("dynamodb")
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE", "chatbot-model"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE", "chatbot-index"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE", "chatbot"))
group_name = "Admin"
chatbot_id = "admin"
model_id = "admin-embedding"

process_number = 1
batch_file_number = 3000
embedding_model_endpoint = "embedding-and-reranker-bce-embedding-and-bge-reranker-43972"
# s3_bucket = "aws-chatbot-knowledge-base-test"
s3_bucket = os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
s3_prefix_list = ["retail/quick_reply/quick_reply_ingestion_data.jsonl",
                  "retail/intent_data/intent_ingestion_data.jsonl",
                  "retail/quick_reply/shouhou_wuliu.jsonl",
                  "retail/goods_info/goods_info.jsonl",
                  "demo/default_intent.jsonl"]
workspace_id_list = ["retail-quick-reply", "retail-intent", "retail-shouhou-wuliu", "goods-info", "default-intent-2"]
index_type_list = ["qq", "qq", "qq", "qq", "qq"]
op_type_list = ["update", "update", "update", "update", "update"]
# op_type_list = ["update", "create", "create", "create", "update"]
local_file_list = ["poc/goods_data/quick_reply/quick_reply_ingestion_data_v2.jsonl",
                   "poc/intent_data/intent_ingestion_data.jsonl",
                   "poc/goods_data/quick_reply/shouhou_wuliu.jsonl",
                   "poc/goods_data/detail/goods_info.jsonl",
                   "../online/lambda_intention_detection/intention_utils/default_intent.jsonl"]

sl1 = slice(0,3)
sl2 = slice(4,5)

workspace_id_list = workspace_id_list[sl1] + workspace_id_list[sl2]
index_type_list = index_type_list[sl1] + index_type_list[sl2]
op_type_list = op_type_list[sl1] + op_type_list[sl2]
local_file_list = local_file_list[sl1] + local_file_list[sl2]

for s3_prefix, workspace_id, index_type, local_file, op_type in zip(s3_prefix_list, workspace_id_list, index_type_list, local_file_list, op_type_list):
    s3_utils.delete_s3_file(s3_bucket, s3_prefix)
    s3_utils.upload_file_to_s3(s3_bucket, s3_prefix, local_file)
    embedding_model_type = sfn_handler.initiate_model(model_table, group_name, model_id)
    tag = workspace_id
    index_id = workspace_id
    sfn_handler.initiate_index(index_table, group_name, index_id, model_id, index_type, tag)
    sfn_handler.initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id, index_type, tag)
    for i in range(process_number):
        command = f"""python3 glue-job-script.py --batch_indice {i} --batch_file_number {batch_file_number} \
            --s3_prefix {s3_prefix} --s3_bucket {s3_bucket} \
            --index_type {index_type} --embedding_model_endpoint {embedding_model_endpoint} \
            --operation_type={op_type} --chatbot_id={chatbot_id} --index_id {index_id} --embedding_model_type bce"""
        print(command)
        os.system(command)
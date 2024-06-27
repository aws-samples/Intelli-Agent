import os
from common_logic.common_utils import s3_utils

from dotenv import load_dotenv
try:
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__),'../../online/lambda_main/test/.env')
    )
except:
    print("cannot find .env")

# run multiple process ingestion

process_number = 1
batch_file_number = 3000
embedding_model_endpoint = "embedding-and-reranker-bce-embedding-and-bge-reranker-43972"
s3_bucket = "aws-chatbot-knowledge-base-test"
s3_prefix_list = ["retail/quick_reply/quick_reply_ingestion_data.jsonl",
                  "retail/intent_data/intent_ingestion_data.jsonl",
                  "retail/quick_reply/quick_reply_ingestion_data.jsonl",
                  "retail/goods_info/goods_info.jsonl",
                  "demo/yb_aos_examples.jsonl"]
workspace_id_list = ["retail-quick-reply", "retail-intent", "retail-shouhou-wuliu", "goods_info", "yb_intent"]
index_type_list = ["qq", "qq", "qq", "qq", "qq"]
op_type_list = ["update", "update", "update", "update", "update"]
local_file_list = ["poc/goods_data/quick_reply/quick_reply_ingestion_data.jsonl",
                   "poc/intent_data/intent_ingestion_data.jsonl",
                   "poc/goods_data/quick_reply/shouhou_wuliu.jsonl",
                   "poc/goods_data/detail/goods_info.jsonl",
                   "yb_aos_examples.jsonl"]

workspace_id_list = workspace_id_list[3:4]
index_type_list = index_type_list[3:4]
op_type_list = op_type_list[3:4]
local_file_list = local_file_list[3:4]

for s3_prefix, workspace_id, index_type, local_file in zip(s3_prefix_list, workspace_id_list, index_type_list, local_file_list):
    s3_utils.delete_s3_file(s3_bucket, s3_prefix)
    s3_utils.upload_file_to_s3(s3_bucket, s3_prefix, local_file)
    for i in range(process_number):
        command = f"python3 glue-job-script.py --batch_indice {i} --batch_file_number {batch_file_number} \
                --s3_prefix {s3_prefix} --s3_bucket {s3_bucket} --workspace_id {workspace_id} \
                --index_type {index_type} --embedding_model_endpoint {embedding_model_endpoint} --operation_type=update"
        print(command)
        os.system(command)
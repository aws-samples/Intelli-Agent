import os
from common_utils import s3_utils

# run multiple process ingestion

process_number = 1
batch_file_number = 3000
embedding_model_endpoint = "embedding-and-reranker-bce-embedding-and-bge-reranker-43972"
s3_bucket = "aws-chatbot-knowledge-base-test"
s3_prefix_list = ["retail/quick_reply/quick_reply_ingestion_data.jsonl", "retail/intent_data/intent_ingestion_data.jsonl", "retail/quick_reply/quick_reply_ingestion_data.jsonl", "retail/quick_reply/shouhou_wuliu.jsonl"]
workspace_id_list = ["retail-quick-reply", "retail-intent", "retail-shouhou-wuliu", "yb_intent"]
index_type_list = ["qq", "qq", "qq", "qq"]
op_type_list = ["update", "update", "update", "update"]
local_file_list = ["poc/goods_data/quick_reply/quick_reply_ingestion_data.jsonl",
                   "poc/intent_data/intent_ingestion_data.jsonl",
                   "poc/goods_data/quick_reply/shouhou_wuliu.jsonl",
                   "yb_aos_examples.jsonl"]

workspace_id_list = workspace_id_list[:-1]
index_type_list = index_type_list[:-1]
op_type_list = op_type_list[:-1]
local_file_list = local_file_list[:-1]

for s3_prefix, workspace_id, index_type, local_file in zip(s3_prefix_list, workspace_id_list, index_type_list, local_file_list):
    s3_utils.delete_s3_file(s3_bucket, s3_prefix)
    s3_utils.upload_file_to_s3(s3_bucket, s3_prefix, local_file)
    for i in range(process_number):
        command = f"python3 glue-job-script.py --batch_indice {i} --batch_file_number {batch_file_number} \
                --s3_prefix {s3_prefix} --s3_bucket {s3_bucket} --workspace_id {workspace_id} \
                --index_type {index_type} --embedding_model_endpoint {embedding_model_endpoint} --operation_type=update"
        print(command)
        os.system(command)
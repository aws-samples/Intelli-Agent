import os
import sys
import time 
from datetime import datetime,timezone

sys.path.append('../online')
sys.path.append('../etl')


from dotenv import load_dotenv
try:
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__),'../../online/lambda_main/test/.env')
    )
except:
    print("cannot find .env")


from common_logic.common_utils import s3_utils
import boto3
import sfn_handler
# run multiple process ingestion

dynamodb = boto3.resource("dynamodb")
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME", "chatbot-model"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME", "chatbot-index"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME", "chatbot"))
group_name = "Admin"
chatbot_id = "admin"
model_id = "admin-embedding"

process_number = 1
batch_file_number = 3000
embedding_model_endpoint = "embedding-and-reranker-bce-embedding-and-bge-reranker-43972"

s3_prefix_base = "."

files = [
    # {
    #     "workspace_id": "default",
    #     "local_path":"/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/docs/intention/default_intent_aos_examples.jsonl",
    #     "index_type": "intention",
    #     "op_type": "update",
    #     "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    # },
    # {
    #     "workspace_id": "sso_poc",
    #     "local_path": "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/sso_poc/memgpt2310.08560v2.pdf",
    #     "index_type": "qd",
    #     "op_type": "update",
    #     "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    # },
    # {
    # "workspace_id": "sso_poc",
    # "local_path": "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/sso_poc/Morgan_Stanley_Oct_21_(EMEA).pdf",
    # "index_type": "qd",
    # "op_type": "update",
    # "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    # }
    # {
    # "workspace_id": "hanxu_poc",
    # "local_path": "/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/poc_from_hanxu/FAQ_TEST_20240412_chk.xlsx",
    # "index_type": "qq",
    # "op_type": "update",
    # "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    # }
    # bigo injection
    {
    "workspace_id": "bigo_qd",
    "local_path": "/home/ubuntu/pytorch_gpu_base_ubuntu_uw2_workplace/csdc/llm-bot-env/llm-bot/poc/bigo/qd/bigo_qd.pdf",
    "index_type": "qd",
    "op_type": "update",
    "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    },
    {
    "workspace_id": "bigo_qq",
    "local_path": "/home/ubuntu/pytorch_gpu_base_ubuntu_uw2_workplace/csdc/llm-bot-env/llm-bot/poc/bigo/qq/bigo_qq.jsonl",
    "index_type": "qq",
    "op_type": "update",
    "s3_bucket": os.environ.get("RES_BUCKET", "aws-chatbot-knowledge-base-test")
    }
]

start_time = time.time()

for file in files:
    s3_prefix = os.path.join(s3_prefix_base,os.path.basename(file['local_path']))
    workspace_id = file['workspace_id']
    index_type = file['index_type']
    op_type = file['op_type']
    local_file = file['local_path']
    s3_bucket = file['s3_bucket']

    s3_utils.delete_s3_file(s3_bucket, s3_prefix)
    s3_utils.upload_file_to_s3(s3_bucket, s3_prefix, local_file)
    
    create_time = str(datetime.now(timezone.utc))
    embedding_model_type = sfn_handler.initiate_model(
        model_table,
        group_name,
        model_id,
        embedding_model_endpoint,
        create_time
        )
    tag = workspace_id
    index_id = f"{chatbot_id}-{index_type}-{workspace_id}"
    print(index_id)

    sfn_handler.initiate_index(index_table, group_name, index_id, model_id, index_type, tag, create_time)
    sfn_handler.initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id, index_type, tag,create_time)
    for i in range(process_number):
        command = f"""{sys.executable} glue-job-script.py --batch_indice {i} --batch_file_number {batch_file_number} \
            --s3_prefix "{s3_prefix}" --s3_bucket {s3_bucket} \
            --index_type {index_type} --embedding_model_endpoint {embedding_model_endpoint} \
            --operation_type={op_type} --chatbot_id={chatbot_id} --index_id {index_id} --embedding_model_type {embedding_model_type}"""
        print(command)
        os.system(command)
        print("current elapsed time: ",time.time()-start_time)

print("total elapsed time: ",time.time()-start_time)
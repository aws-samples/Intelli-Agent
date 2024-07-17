import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging

import boto3
import sys

from functions.functions_utils.retriever.utils.aos_retrievers import QueryDocumentKNNRetriever, QueryDocumentBM25Retriever, QueryQuestionRetriever
from functions.functions_utils.retriever.utils.reranker import BGEReranker, MergeReranker
from functions.functions_utils.retriever.utils.context_utils import retriever_results_format
from functions.functions_utils.retriever.utils.websearch_retrievers import GoogleRetriever

from langchain.retrievers import ContextualCompressionRetriever, AmazonKnowledgeBasesRetriever
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.schema.runnable import (
    RunnableLambda,
    RunnablePassthrough,
)
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
from common_logic.common_utils.chatbot_utils import ChatbotManager

logger = logging.getLogger("retriever")
logger.setLevel(logging.INFO)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

chatbot_table_name = os.environ.get("CHATBOT_TABLE", "")
model_table_name = os.environ.get("MODEL_TABLE", "")
index_table_name = os.environ.get("INDEX_TABLE", "")
dynamodb = boto3.resource("dynamodb")
chatbot_table = dynamodb.Table(chatbot_table_name)
model_table = dynamodb.Table(model_table_name)
index_table = dynamodb.Table(index_table_name)
chatbot_manager = ChatbotManager(chatbot_table, index_table, model_table)

region = boto3.Session().region_name

knowledgebase_client = boto3.client("bedrock-agent-runtime", region)
sm_client = boto3.client("sagemaker-runtime")

def get_bedrock_kb_retrievers(knowledge_base_id_list, top_k:int):
    retriever_list = [
        AmazonKnowledgeBasesRetriever(
            knowledge_base_id=knowledge_base_id,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": top_k}})
        for knowledge_base_id in knowledge_base_id_list
    ]
    return retriever_list

def get_websearch_retrievers(top_k:int):
    retriever_list = [
        GoogleRetriever(top_k)
    ]
    return retriever_list

def get_custom_qd_retrievers(qd_config_list:list[dict],using_bm25=False):
    retriever_list = [
        QueryDocumentKNNRetriever(
            **{
                "index": config['indexId'],
                "top_k": config['top_k'],
                "embedding_model_endpoint": config['modelIds']['embedding']['ModelEndpoint'],
                "target_model": config['modelIds']['embedding']['ModelName'],
                "model_type": "vector",
                "query_key": config.get("query_key","query"),
                "text_field": config.get("text_field","text"),
                "using_whole_doc": config.get("using_whole_doc",False),
                "context_num":config["context_num"],
                "enable_debug": config.get('enable_debug',False)
            }  
        )
        for config in qd_config_list
    ]

    if using_bm25:
        retriever_list += [
                QueryDocumentBM25Retriever(
                    **{
                        "index": config['indexId'],
                        "using_whole_doc": config.get("using_whole_doc",False),
                        "context_num":config["context_num"],
                        "enable_debug": config.get('enable_debug',False)
                    }
                )
                for config in qd_config_list
            ]
    return retriever_list

def get_custom_qq_retrievers(qq_config_list:list[dict]):
    retriever_list = [
        QueryQuestionRetriever(
            **{
                "index": config['indexId'],
                "top_k": config['top_k'],
                "embedding_model_endpoint": config['modelIds']['embedding']['parameter']['ModelEndpoint'],
                "target_model": config['modelIds']['embedding']['parameter']['ModelName'],
                "model_type": "vector",
                "query_key": config.get("query_key","query"),
                "enable_debug": config.get('enable_debug',False)
            }
        )
        for config in qq_config_list
    ]
    return retriever_list

def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    if len(reranker_config):
        default_reranker_config = {
            "enable_debug": False,
            "target_model": "bge_reranker_model.tar.gz",
            "query_key": "query",
            "top_k": 10
        }
        reranker_config = {**default_reranker_config, **reranker_config}
        compressor = BGEReranker(**reranker_config)
    else:
        compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    whole_chain = RunnablePassthrough.assign(
            docs=compression_retriever | RunnableLambda(retriever_results_format))
    return whole_chain


retriever_dict = {
    "qq": get_custom_qq_retrievers,
    "qd": get_custom_qd_retrievers,
    "websearch": get_websearch_retrievers,
    "bedrock_kb": get_bedrock_kb_retrievers,
}

def get_custom_retrievers(retrievers,retriever_type):
    return retriever_dict[retriever_type](retrievers)

@chatbot_lambda_call_wrapper
def lambda_handler(event, context=None):
    event_body = event
    retriever_type = event['type']
    # retriever_list = []
    # for retriever in event_body["retrievers"]:
    retriever_list = get_custom_retrievers(event_body["retrievers"],retriever_type)
    rerankers = event_body.get("rerankers", None)
    if rerankers:
        reranker_config = rerankers[0]["config"]
    else:
        reranker_config = {}
    if len(retriever_list) > 0:
        whole_chain = get_whole_chain(retriever_list, reranker_config)
    else:
        whole_chain = RunnablePassthrough.assign(docs = lambda x: [])
    docs = whole_chain.invoke({"query": event_body["query"], "debug_info": {}})
    return {"code":0, "result": docs}

if __name__ == "__main__":
    query = '''test'''
    event = {
        "body":
            json.dumps(
                {
                    "retrievers": [
                        {
                            "type": "qq",
                            "index_ids": ["test"],
                            "config": {
                                "top_k": 10,
                            }
                        },
                    ],
                    "rerankers": [
                        {
                            "type": "reranker",
                            "config": {
                                "enable_debug": False,
                                "target_model": "bge_reranker_model.tar.gz"
                            }
                        }
                    ],
                    "query": query
                }
            )
    }
    response = lambda_handler(event, None)
    print(response)
import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging

import boto3
import sys

from functions.lambda_retriever.utils.aos_retrievers import QueryDocumentKNNRetriever, QueryDocumentBM25Retriever, QueryQuestionRetriever
from functions.lambda_retriever.utils.reranker import BGEReranker, MergeReranker
from functions.lambda_retriever.utils.context_utils import retriever_results_format
from functions.lambda_retriever.utils.websearch_retrievers import GoogleRetriever

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

# def get_custom_qd_retrievers(workspace_ids, qd_config, using_bm25=False):
def get_custom_qd_retrievers(chatbot, index_tag, retriever_config["config"], using_bm25=False):
    default_qd_config = {
        "using_whole_doc": False,
        "context_num": 1,
        "top_k": 10,
        "query_key": "query"
    }
    qd_config = {**default_qd_config, **qd_config}
    index_dict = chatbot.get_index_dict()
    retriever_list = [
        QueryDocumentKNNRetriever(
            index_id,
            index_type,
            index_tag,
            chatbot,
            **qd_config
        )
        for workspace in workspace_list
    ] + [
        QueryDocumentBM25Retriever(
            workspace=workspace,
            **qd_config
        )
        for workspace in workspace_list
    ]
    return retriever_list

def get_custom_qq_retrievers(chatbot, index_tag, qq_config):
    default_qq_config = {
        "top_k": 10,
        "query_key": "query"
    }
    qq_config = {**default_qq_config, **qq_config}
    index_dict = chatbot.get_index_dict()
    retriever_list = [
        QueryQuestionRetriever(
            index_id,
            index_type,
            index_tag,
            chatbot,
            **qq_config
        )
        for index_id, index_type in index_dict.items()
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

def get_custom_retrievers(group_name, index_tag, retriever_config):
    retriever_type = retriever_config["type"]
    chatbot = chatbot_manager.get_chatbot(group_name, retriever_config["chatbot_id"])
    return retriever_dict[retriever_type](chatbot, index_tag, retriever_config["config"])

@chatbot_lambda_call_wrapper
def lambda_handler(event, context=None):
    event_body = event
    group_name = event_body["chatbot_config"]["group_name"]
    index_tag = event_body["chatbot_config"]["index_tag"]
    retriever_list = []
    for retriever_config in event_body["retrievers"]:
        retriever_type = retriever_config["type"]
        retriever_list.extend(get_custom_retrievers(group_name, index_tag, retriever_config))
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
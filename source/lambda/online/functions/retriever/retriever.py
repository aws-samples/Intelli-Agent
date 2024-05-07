import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging
import time
import uuid

import boto3
import sys

from utils.aos_retrievers import QueryDocumentKNNRetriever, QueryDocumentBM25Retriever, QueryQuestionRetriever
from utils.reranker import BGEReranker, BGEM3Reranker, MergeReranker
from utils.context_utils import retriever_results_format
from utils.websearch_retrievers import GoogleRetriever
from utils.workspace_utils import WorkspaceManager

from langchain.retrievers import ContextualCompressionRetriever, AmazonKnowledgeBasesRetriever
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

logger = logging.getLogger("retriever")
logger.setLevel(logging.INFO)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)



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

def get_custom_qd_retrievers(qd_config):
    workspace_list = get_workspace_list(qd_config["workspace_ids"])
    using_whole_doc = qd_config["using_whole_doc"]
    context_num = qd_config["context_num"]
    retriever_top_k = qd_config["top_k"]
    qd_query_key = qd_config["query_key"]
    retriever_list = [
        QueryDocumentKNNRetriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            #   "zh", zh_embedding_endpoint
        )
        for workspace in workspace_list
    ] + [
        QueryDocumentBM25Retriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            #   "zh", zh_embedding_endpoint
        )
        for workspace in workspace_list
    ]
    return retriever_list

def get_custom_qq_retrievers(qq_config):
    workspace_list = get_workspace_list(qq_config["workspace_ids"])
    retriever_list = [
        QueryQuestionRetriever(
            workspace,
            size=qq_config["top_k"],
        )
        for workspace in workspace_list
    ]
    return retriever_list

def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    if reranker_config["enable_reranker"]:
        compressor = BGEReranker(query_key=reranker_config["query_key"],
                                 enable_debug=reranker_config['enable_debug'],
                                 target_model=reranker_config['rerank_target_model'])
    else:
        compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    whole_chain = RunnablePassthrough.assign(
            docs=compression_retriever | RunnableLambda(retriever_results_format))
    return whole_chain

def get_workspace_list(workspace_ids):
    workspace_list = []
    for workspace_id in workspace_ids:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace or "index_type" not in workspace:
            logger.warning(f"workspace {workspace_id} not found")
            continue
        workspace_list.append(workspace)
    return workspace_list

retriever_dict = {
    "custom_qq_retrievers": get_custom_qq_retrievers,
    "custom_qd_retrievers": get_custom_qd_retrievers,
    "websearch_retrievers": get_websearch_retrievers,
    "bedrock_kb_retrievers": get_bedrock_kb_retrievers,
}

# @handle_error
def lambda_handler(event, context):
    event_body = json.loads(event["body"])
    retriever_list = []
    for retriever_type in event_body["retrievers"]:
        retriever_list.extend(retriever_dict[retriever_type](event_body["retrievers"][retriever_type]))
    whole_chain = get_whole_chain(retriever_list, event_body["reranker"])
    whole_chain.invoke({"query": event_body["query"], "debug_info": {}})

if __name__ == "__main__":
    event = {
        "body":
            json.dumps(
                {
                    "retrievers": {
                        "custom_qq_retrievers": {
                            "workspace_ids": ["dgr-faq-qq-bce", "mkt-faq-qq-bce"],
                            "top_k": 10,
                            "query_key": "query"
                        },
                        "custom_qd_retrievers": {
                            "workspace_ids": ["event-qd-bce"],
                            "context_num": 2,
                            "top_k": 10,
                            "query_key": "query",
                            "using_whole_doc": True
                        }
                    },
                    "reranker": {
                        "enable_reranker": True,
                        "query_key": "query",
                        "enable_debug": False,
                        "rerank_target_model": "bge_reranker_model.tar.gz"
                    },
                    "query": "亚马逊"
                }
            )
    }
    response = lambda_handler(event, None)
    print(response)
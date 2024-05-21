import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging
import time
import uuid

import boto3
import sys

from functions.lambda_retriever.utils.aos_retrievers import QueryDocumentKNNRetriever, QueryDocumentBM25Retriever, QueryQuestionRetriever
from functions.lambda_retriever.utils.reranker import BGEReranker, BGEM3Reranker, MergeReranker
from functions.lambda_retriever.utils.context_utils import retriever_results_format
from functions.lambda_retriever.utils.websearch_retrievers import GoogleRetriever
from functions.lambda_retriever.utils.workspace_utils import WorkspaceManager

from langchain.retrievers import ContextualCompressionRetriever, AmazonKnowledgeBasesRetriever
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper

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

def get_custom_qd_retrievers(workspace_ids, qd_config):
    default_qd_config = {
        "using_whole_doc": False,
        "context_num": 1,
        "top_k": 10,
        "query_key": "query"
    }
    qd_config = {**default_qd_config, **qd_config}
    workspace_list = get_workspace_list(workspace_ids)
    retriever_list = [
        QueryDocumentKNNRetriever(
            workspace=workspace,
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

def get_custom_qq_retrievers(workspace_ids, qq_config):
    default_qq_config = {
        "top_k": 10,
        "query_key": "query"
    }
    qq_config = {**default_qq_config, **qq_config}
    workspace_list = get_workspace_list(workspace_ids)
    retriever_list = [
        QueryQuestionRetriever(
            workspace,
            **qq_config
        )
        for workspace in workspace_list
    ]
    return retriever_list

def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    if len(reranker_config):
        default_reranker_config = {
            "enable_debug": False,
            "target_model": "bge_reranker_model.tar.gz",
            "query_key": "query"
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
    "qq": get_custom_qq_retrievers,
    "qd": get_custom_qd_retrievers,
    "websearch": get_websearch_retrievers,
    "bedrock_kb": get_bedrock_kb_retrievers,
}

def get_custom_retrievers(retriever_config):
    retriever_type = retriever_config["type"]
    return retriever_dict[retriever_type](retriever_config["workspace_ids"], retriever_config["config"])

@chatbot_lambda_call_wrapper
def lambda_handler(event, context=None):
    event_body = event
    retriever_list = []
    for retriever_config in event_body["retrievers"]:
        retriever_type = retriever_config["type"]
        retriever_list.extend(get_custom_retrievers(retriever_config))
    rerankers = event_body.get("rerankers", None)
    if rerankers:
        reranker_config = rerankers[0]["config"]
    else:
        reranker_config = {}
    whole_chain = get_whole_chain(retriever_list, reranker_config)
    docs = whole_chain.invoke({"query": event_body["query"], "debug_info": {}})
    return {"code":0, "result": docs}

if __name__ == "__main__":
    query = '''
What's the most appropriate way to proceed in the following situation?:
(single choice)

The Player filled out an Application Form but forgot to add his list of owned 5☆ Characters to the Form and wants to update it before the result is known.

A) Ask the Player to provide the updated information and send it to a GM handling account issues to update the Application Form.

B) Inform the Player that the list of 5☆ Characters isn't useful information to recover the HoYoverse Account and that he should only provide replies to the existing questions.  

C) Advise the Player to fill out a new Application Form with the updated information.

D) Reject the Player's Request and inform him that the Application Form information can't be modified/changed.'''
    event = {
        "body":
            json.dumps(
                {
                    "retrievers": [
                        {
                            "type": "qd",
                            "workspace_ids": ["mihoyo-test"],
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
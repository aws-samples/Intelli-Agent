from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.retrievers import (
    AmazonKnowledgeBasesRetriever,
    ContextualCompressionRetriever,
)
from lambda_retriever.utils.reranker import MergeReranker
from lambda_retriever.utils.context_utils import retriever_results_format
from lambda_retriever.utils.aos_retrievers import (
    QueryDocumentBM25Retriever,
    QueryDocumentKNNRetriever,
    QueryQuestionRetriever,
)
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
import boto3
import sys
import logging
import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"


logger = logging.getLogger("retriever")
logger.setLevel(logging.INFO)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

region = boto3.Session().region_name

knowledgebase_client = boto3.client("bedrock-agent-runtime", region)
sm_client = boto3.client("sagemaker-runtime")


def get_bedrock_kb_retrievers(knowledge_base_id_list, top_k: int):
    retriever_list = [
        AmazonKnowledgeBasesRetriever(
            knowledge_base_id=knowledge_base_id,
            retrieval_config={"vectorSearchConfiguration": {
                "numberOfResults": top_k}},
        )
        for knowledge_base_id in knowledge_base_id_list
    ]
    return retriever_list


def get_custom_qd_retrievers(retriever_config, using_bm25=False):
    default_qd_config = {
        "using_whole_doc": False,
        "context_num": 1,
        "top_k": 10,
        "query_key": "query",
    }
    # qd_config = {**default_qd_config, **qd_config}
    retriever_list = [QueryDocumentKNNRetriever(retriever_config)]
    if using_bm25:
        retriever_list += [QueryDocumentBM25Retriever(retriever_config)]
    return retriever_list


def get_custom_qq_retrievers(retriever_config):
    default_qq_config = {"top_k": 10, "query_key": "query"}

    return [
        QueryQuestionRetriever(
            retriever_config,
            # **qq_config
        )
    ]


def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    # if len(reranker_config):
    #     default_reranker_config = {
    #         "enable_debug": False,
    #         "target_model": "bge_reranker_model.tar.gz",
    #         "query_key": "query",
    #         "top_k": 10
    #     }
    #     reranker_config = {**default_reranker_config, **reranker_config}
    #     compressor = BGEReranker(**reranker_config)
    # else:
    compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    whole_chain = RunnablePassthrough.assign(
        docs=compression_retriever | RunnableLambda(retriever_results_format)
    )
    return whole_chain


def get_custom_retrievers(retriever_config, retriever_type="qd"):
    retriever_dict = {
        "qq": get_custom_qq_retrievers,
        "qd": get_custom_qd_retrievers,
        "bedrock_kb": get_bedrock_kb_retrievers,
    }
    # retriever_type = retriever_config["type"]
    return retriever_dict[retriever_type](retriever_config)


@chatbot_lambda_call_wrapper
def lambda_handler(event, context=None):
    event_body = event
    retriever_list = []
    retriever_type = event_body["type"]
    for retriever_config in event_body["retrievers"]:
        # retriever_type = retriever_config["type"]
        retriever_list.extend(get_custom_retrievers(
            retriever_config, retriever_type))

    # Re-rank not used.
    # rerankers = event_body.get("rerankers", None)
    # if rerankers:
    #     reranker_config = rerankers[0]["config"]
    # else:
    #     reranker_config = {}
    reranker_config = {}
    if len(retriever_list) > 0:
        whole_chain = get_whole_chain(retriever_list, reranker_config)
    else:
        whole_chain = RunnablePassthrough.assign(docs=lambda x: [])
    docs = whole_chain.invoke({"query": event_body["query"], "debug_info": {}})
    return {"code": 0, "result": docs}


if __name__ == "__main__":
    query = """test"""
    event = {
        "body": json.dumps(
            {
                "retrievers": [
                    {
                        "index": "test-intent",
                        "config": {"top_k": "3"},
                        "embedding": {
                            "type": "Bedrock",
                            "model_id": "cohere.embed-multilingual-v3",
                        },
                    }
                ],
                "query": query,
                "type": "qq",
            }
        )
    }

    event2 = {
        "body": json.dumps(
            {
                "retrievers": [
                    {
                        "index": "test-qa",
                        "config": {
                            "top_k": "3",
                            "vector_field_name": "sentence_vector",
                            "text_field_name": "paragraph",
                            "source_field_name": "source",
                        },
                        "embedding": {
                            "type": "Bedrock",
                            "model_id": "amazon.titan-embed-text-v2:0",
                        },
                    }
                ],
                "query": query,
                "type": "qd",
            }
        )
    }

    response = lambda_handler(event2, None)
    print(response)

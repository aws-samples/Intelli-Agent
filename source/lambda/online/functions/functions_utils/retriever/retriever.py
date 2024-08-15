import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging
import sys

import boto3
from common_logic.common_utils.chatbot_utils import ChatbotManager
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
from functions.functions_utils.retriever.utils.aos_retrievers import (
    QueryDocumentBM25Retriever,
    QueryDocumentKNNRetriever,
    QueryQuestionRetriever,
)
from functions.functions_utils.retriever.utils.context_utils import (
    retriever_results_format,
)
from functions.functions_utils.retriever.utils.reranker import (
    BGEReranker,
    MergeReranker,
)
from functions.functions_utils.retriever.utils.websearch_retrievers import (
    GoogleRetriever,
)
from langchain.retrievers import (
    AmazonKnowledgeBasesRetriever,
    ContextualCompressionRetriever,
)
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

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


def get_bedrock_kb_retrievers(knowledge_base_id_list, top_k: int):
    retriever_list = [
        AmazonKnowledgeBasesRetriever(
            knowledge_base_id=knowledge_base_id,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": top_k}},
        )
        for knowledge_base_id in knowledge_base_id_list
    ]
    return retriever_list


def get_websearch_retrievers(top_k: int):
    retriever_list = [GoogleRetriever(top_k)]
    return retriever_list


def get_custom_qd_retrievers(config: dict, using_bm25=False):
    qd_retriever = QueryDocumentKNNRetriever(**config)

    if using_bm25:
        bm25_retrievert = QueryDocumentBM25Retriever(
            **{
                "index_name": config["index_name"],
                "using_whole_doc": config.get("using_whole_doc", False),
                "context_num": config["context_num"],
                "enable_debug": config.get("enable_debug", False),
            }
        )
        return [qd_retriever, bm25_retrievert]
    return [qd_retriever]


def get_custom_qq_retrievers(config: dict):
    qq_retriever = QueryQuestionRetriever(model_type="vector", **config)
    return [qq_retriever]


def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    # if len(reranker_config):
    #     default_reranker_config = {
    #         "enable_debug": False,
    #         "target_model": "bge_reranker_model.tar.gz",
    #         "top_k": 10,
    #     }
    #     reranker_config = {**default_reranker_config, **reranker_config}
    #     compressor = BGEReranker(**reranker_config)
    # else:
    #     compressor = MergeReranker()

    # Disable Reranker for AICS Guidance
    compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    whole_chain = RunnablePassthrough.assign(
        docs=compression_retriever | RunnableLambda(retriever_results_format)
    )
    return whole_chain


retriever_dict = {
    "qq": get_custom_qq_retrievers,
    "intention": get_custom_qq_retrievers,
    "qd": get_custom_qd_retrievers,
    "websearch": get_websearch_retrievers,
    "bedrock_kb": get_bedrock_kb_retrievers,
}


def get_custom_retrievers(retriever):
    return retriever_dict[retriever["index_type"]](retriever)


def lambda_handler(event, context=None):
    logger.info(f"Retrieval event: {event}")
    event_body = event
    event_body["retrievers"].append(
        {
            "index_type": "qd",
            "index_name": "test",
            "vector_field": "sentence_vector",
            "source_field": "source",
            "text_field": "paragraph",
        }
    )
    retriever_list = []
    print(retriever_list)
    for retriever in event_body["retrievers"]:
        retriever_list.extend(get_custom_retrievers(retriever))
    rerankers = event_body.get("rerankers", None)
    if rerankers:
        reranker_config = rerankers[0]["config"]
    else:
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
                        "type": "qq",
                        "index_ids": ["test"],
                        "config": {
                            "top_k": 10,
                        },
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz",
                        },
                    }
                ],
                "query": query,
            }
        )
    }
    response = lambda_handler(event, None)
    print(response)

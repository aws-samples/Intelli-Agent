from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
from langchain.retrievers import (
    ContextualCompressionRetriever,
)
from common_logic.langchain_integration.retrievers.utils.reranker import (
    BGEReranker,
    MergeReranker,
)
from common_logic.langchain_integration.retrievers.utils.context_utils import (
    retriever_results_format,
)
from common_logic.langchain_integration.retrievers.utils.aos_retrievers import (
    QueryDocumentBM25Retriever,
    QueryDocumentKNNRetriever,
    QueryQuestionRetriever,
)
from common_logic.common_utils.chatbot_utils import ChatbotManager
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

kb_enabled = os.environ["KNOWLEDGE_BASE_ENABLED"].lower() == "true"
kb_type = json.loads(os.environ["KNOWLEDGE_BASE_TYPE"])
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
            retrieval_config={"vectorSearchConfiguration": {
                "numberOfResults": top_k}},
        )
        for knowledge_base_id in knowledge_base_id_list
    ]
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
    qq_retriever = QueryQuestionRetriever(**config)
    return [qq_retriever]


def get_whole_chain(retriever_list, reranker_config):
    lotr = MergerRetriever(retrievers=retriever_list)
    if len(reranker_config):
        default_reranker_config = {
            "enable_debug": False,
            "target_model": "bge_reranker_model.tar.gz",
            "top_k": 10,
        }
        reranker_config = {**default_reranker_config, **reranker_config}
        compressor = BGEReranker(**reranker_config)
    else:
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
    "bedrock_kb": get_bedrock_kb_retrievers,
}


def get_custom_retrievers(retriever):
    return retriever_dict[retriever["index_type"]](retriever)


def lambda_handler(event, context=None):
    logger.info(f"Retrieval event: {event}")
    event_body = event
    retriever_list = []
    for retriever in event_body["retrievers"]:
        if not kb_enabled:
            retriever["vector_field"] = "sentence_vector"
            retriever["source_field"] = "source"
            retriever["text_field"] = "paragraph"
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
        "retrievers": [
            {
                "index_type": "qd",
                "top_k": 5,
                "context_num": 1,
                "using_whole_doc": False,
                "query_key": "query",
                "index_name": "admin-qd-default",
                "kb_type": "aos",
                "target_model": "amazon.titan-embed-text-v1",
                "embedding_model_endpoint": "amazon.titan-embed-text-v1",
                "model_type": "bedrock",
                "group_name": "Admin",
            }
        ],
        "rerankers": [],
        "llm_config": {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "model_kwargs": {"temperature": 0.01, "max_tokens": 1000},
            "endpoint_name": "",
        },
        "query": "亚马逊云计算服务可以通过超文本传输协议（HTTP）访问吗？",
    }
    response = lambda_handler(event, None)
    print(response)

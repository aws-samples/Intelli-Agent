from .. import retriever

# from ..retriever import QueryDocumentRetriever, QueryQuestionRetriever,index_results_format
from ..constant import IntentType, INTENT_RECOGNITION_TYPE

# from functools import partial
from langchain.schema.runnable import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
)
# from ..llm_utils import Model as LLM_Model
# from ..llm_utils.llm_chains import LLMChain
# from langchain.prompts import PromptTemplate
# import re

from functools import lru_cache, partial
import hashlib
import traceback
import threading
import boto3
import logging
import os
import json
from typing import List, Dict
from random import Random

# from ..preprocess_utils import is_api_query,get_service_name
from ..langchain_utils import chain_logger, RunnableNoneAssign
from ..embeddings_utils import BGEM3EmbeddingSagemakerEndpoint
from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)
# from langchain_community.embeddings.sagemaker_endpoint import (
#     SagemakerEndpointEmbeddings
# )

from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

opensearch_client_lock = threading.Lock()
abs_file_dir = os.path.dirname(__file__)
intent_example_path = os.path.join(abs_file_dir, "intent_examples", "examples.json")


class LangchainOpenSearchClient:
    instance = None

    def __new__(
        cls,
        index_name,
        embedding_endpoint_name,
        host=os.environ.get("aos_endpoint", None),
    ):
        identity = f"{index_name}_{host}_{embedding_endpoint_name}"
        with opensearch_client_lock:
            if cls.instance is not None and cls.instance._identity == identity:
                return cls.instance
            obj = cls.create(index_name, embedding_endpoint_name, host=host)
            obj._identity = identity
            cls.instance = obj
            return obj

    @classmethod
    def create(
        cls,
        index_name,
        embedding_endpoint_name,
        host=os.environ.get("aos_endpoint", None),
        region_name=os.environ["AWS_REGION"],
    ):
        embedding = BGEM3EmbeddingSagemakerEndpoint(
            endpoint_name=embedding_endpoint_name, region_name=region_name
        )
        port = int(os.environ.get("AOS_PORT", 443))
        opensearch_url = f"https://{host}:{port}"
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region_name,
            "es",
            session_token=credentials.token,
        )
        opensearch_client = OpenSearchVectorSearch(
            index_name=index_name,
            embedding_function=embedding,
            opensearch_url=opensearch_url,
        )
        return opensearch_client


class IntentRecognitionAOSIndex:
    def __init__(
        self,
        intent_example_path=intent_example_path,
        index_name=None,
        embedding_endpoint_name=None,
        host=os.environ.get("aos_endpoint", None),
    ):
        if index_name is None:
            index_name = self.create_index_name(
                embedding_endpoint_name=embedding_endpoint_name,
                intent_example_path=intent_example_path,
            )
        self.index_name = index_name
        self.host = host
        self.embedding_endpoint_name = embedding_endpoint_name
        self.opensearch_client = LangchainOpenSearchClient(
            index_name=index_name,
            embedding_endpoint_name=embedding_endpoint_name,
            host=host,
        )

    @staticmethod
    @lru_cache()
    def create_index_name(
        embedding_endpoint_name, intent_example_path=intent_example_path
    ):
        index_name = f"intent_recognition_{embedding_endpoint_name}_{hashlib.md5(open(intent_example_path,'rb').read()).hexdigest()}"
        return index_name

    def check_index_exist(self):
        if_exist = self.opensearch_client.client.indices.exists(self.index_name)
        count = 0
        if if_exist:
            count = self.opensearch_client.client.count(index=self.index_name)["count"]
        if_exist = count > 0
        logger.info(f"{self.index_name} exist: {if_exist}, count: {count}")
        return if_exist

    def ingestion_intent_data(self):
        docs = []
        intent_examples = json.load(open(intent_example_path))["examples"]
        for intent_name, examples in intent_examples.items():
            for example in examples:
                doc = Document(page_content=example, metadata={"intent": intent_name})
                docs.append(doc)
        logger.info(
            f"ingestion intent doc, num: {len(docs)}, index_name: {self.index_name}"
        )
        self.opensearch_client.add_documents(docs)
        logger.info(f"ingestion intent doc, num: {len(docs)}")

    def search(self, query, top_k=5):
        r_docs = self.opensearch_client.similarity_search_with_score(
            query=query, k=top_k
        )
        # r_docs = opensearch_client.similarity_search(datum['question'],k=1)
        ret = [
            {
                "candidate_query": r_doc[0].page_content,
                "intent": r_doc[0].metadata["intent"],
                "score": r_doc[1],
                "origin_query": query,
            }
            for r_doc in r_docs
        ]
        logger.info(f"intent index search results:\n{ret}")

        return ret

    def intent_postprocess_top_1(self, retriever_list: list[dict]):
        retriever_list = sorted(retriever_list, key=lambda x: x["score"])
        intent = retriever_list[-1]["intent"]
        assert IntentType.has_value(intent), intent
        return intent

    def as_check_index_exist_chain(self):
        return RunnableLambda(lambda x: self.check_index_exist())

    def as_search_chain(self, top_k=5):
        return RunnableLambda(lambda x: self.search(x["query"], top_k=top_k))

    def as_ingestion_chain(self):
        chain = RunnableNoneAssign(lambda x: self.ingestion_intent_data())
        return chain

    def as_intent_postprocess_chain(self, method="top_1"):
        if method == "top_1":
            chain = RunnableLambda(self.intent_postprocess_top_1)
            return chain
        else:
            raise TypeError(f"invalid method {method}")

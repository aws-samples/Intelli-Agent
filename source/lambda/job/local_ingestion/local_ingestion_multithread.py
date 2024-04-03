import datetime
import itertools
import json
import logging
import os
import sys
import uuid
import time
import math
import traceback
import contextlib
import threading

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import functools
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import boto3
import chardet
import nltk
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)
from tenacity import retry, stop_after_attempt, wait_exponential

bge_m3_embedding_lock = None
aos_injection_mp = None
aos_injection_task_queue = None
index_create_lock = None


class BGRM3Embedding(Embeddings):
    instance = None

    def __new__(cls):
        if cls.instance is not None:
            return cls.instance
        instance = super().__new__(cls)
        cls.instance = instance
        instance.model = instance.create_model()
        return instance

    def create_model(self):
        from FlagEmbedding import BGEM3FlagModel

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cuda:0")
        logger.info(f"load model successfully")
        return model

    def format_ret(self, ret: dict):
        colbert_vecs_list = []
        for colbert_vecs in ret["colbert_vecs"]:
            colbert_vecs_list.append(colbert_vecs.tolist())

        dense_vecs_list = ret["dense_vecs"].tolist()

        return {
            "colbert_vecs_list": colbert_vecs_list,
            "dense_vecs_list": dense_vecs_list,
        }

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        ret = self.model.encode(
            texts,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=True,
            batch_size=12,
            max_length=512,
        )
        ret = self.format_ret(ret)

        return ret

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        ret = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
            batch_size=12,
            max_length=512,
        )
        ret = self.format_ret(ret)
        return ret


def __bulk_add(
    self: OpenSearchVectorSearch,
    data: Iterable[dict],
    # texts: Iterable[str],
    # embeddings: List[List[float]],
    # metadatas: Optional[List[dict]] = None,
    ids: Optional[List[str]] = None,
    embedding_size: int = None,
    # bulk_size: int = 500,
    **kwargs: Any,
) -> List[str]:
    assert embedding_size is not None, embedding_size
    from langchain_community.vectorstores.opensearch_vector_search import (
        _import_bulk,
        _import_not_found_error,
        _validate_aoss_with_engines,
        _default_text_mapping,
    )

    # _validate_embeddings_and_bulk_size(len(embeddings), bulk_size)
    index_name = kwargs.get("index_name", self.index_name)
    text_field = kwargs.get("text_field", "text")
    engine = kwargs.get("engine", "nmslib")
    space_type = kwargs.get("space_type", "l2")
    ef_search = kwargs.get("ef_search", 512)
    ef_construction = kwargs.get("ef_construction", 512)
    m = kwargs.get("m", 16)
    vector_field = kwargs.get("vector_field", "vector_field")
    max_chunk_bytes = kwargs.get("max_chunk_bytes", 1 * 1024 * 1024)

    _validate_aoss_with_engines(self.is_aoss, engine)

    # dim = len(embeddings[0])
    mapping = _default_text_mapping(
        embedding_size, engine, space_type, ef_search, ef_construction, m, vector_field
    )

    if not mapping:
        mapping = dict()
    bulk = _import_bulk()
    not_found_error = _import_not_found_error()
    # requests = []
    return_ids = []
    mapping = mapping

    with index_create_lock:
        try:
            self.client.indices.get(index=index_name)
        except not_found_error:
            self.client.indices.create(index=index_name, body=mapping)

    def request_generator():
        for i, datum in enumerate(data):
            metadata = datum["metadata"]
            text = datum["text"]
            embedding = datum["embedding"]
            # metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "index",
                "_index": index_name,
                vector_field: embedding,
                text_field: text,
                "metadata": metadata,
            }
            if self.is_aoss:
                request["id"] = _id
            else:
                request["_id"] = _id

            # requests.append(request)
            return_ids.append(_id)
            yield request

    bulk(
        self.client,
        request_generator(),
        max_chunk_bytes=max_chunk_bytes,
        # ignore_status=(200,)
    )
    if not self.is_aoss:
        self.client.indices.refresh(index=index_name)
    return return_ids


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
def _bulk_add(*args, **kwargs):
    try:
        __bulk_add(*args, **kwargs)
    except Exception as e:
        raise RuntimeError(
            f"Catch exception when adding document to OpenSearch: {str(e)[:100]}"
        )


def bulk_add(*args, **kwargs):
    try:
        _bulk_add(*args, **kwargs)
    except Exception as e:
        logger.error(f"bulk add fail: { traceback.format_exc(limit=1)}")


#         return _bulk_ingest_embeddings(
#             self.client,
#             index_name,
#             embeddings,
#             texts,
#             metadatas=metadatas,
#             ids=ids,
#             vector_field=vector_field,
#             text_field=text_field,
#             mapping=mapping,
#             max_chunk_bytes=max_chunk_bytes,
#             is_aoss=self.is_aoss,
#         )(
#     client: Any,
#     index_name: str,
#     embeddings: List[List[float]],
#     texts: Iterable[str],
#     metadatas: Optional[List[dict]] = None,
#     ids: Optional[List[str]] = None,
#     vector_field: str = "vector_field",
#     text_field: str = "text",
#     mapping: Optional[Dict] = None,
#     max_chunk_bytes: Optional[int] = 1 * 1024 * 1024,
#     is_aoss: bool = False,
# ) -> List[str]:

# """Bulk Ingest Embeddings into given index."""
# if not mapping:
#     mapping = dict()

# bulk = _import_bulk()
# not_found_error = _import_not_found_error()
# requests = []
# return_ids = []
# mapping = mapping

# try:
#     client.indices.get(index=index_name)
# except not_found_error:
#     client.indices.create(index=index_name, body=mapping)


# for i, text in enumerate(texts):
#     metadata = metadatas[i] if metadatas else {}
#     _id = ids[i] if ids else str(uuid.uuid4())
#     request = {
#         "_op_type": "index",
#         "_index": index_name,
#         vector_field: embeddings[i],
#         text_field: text,
#         "metadata": metadata,
#     }
#     if is_aoss:
#         request["id"] = _id
#     else:
#         request["_id"] = _id
#     requests.append(request)
#     return_ids.append(_id)


sys.path.append("dep")

from boto3.dynamodb.conditions import Attr, Key
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# from langchain.vectorstores import OpenSearchVectorSearch
# from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)

from llm_bot_dep import sm_utils
from llm_bot_dep.constant import SplittingType
from llm_bot_dep.ddb_utils import WorkspaceManager
from llm_bot_dep.embeddings import get_embedding_info
from llm_bot_dep.enhance_utils import EnhanceWithBedrock
from llm_bot_dep.loaders.auto import cb_process_object
from llm_bot_dep.storage_utils import save_content_to_s3
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt, wait_exponential


import os
import psutil


def get_program_memory_usage(pid=None):
    if pid is None:
        pid = os.getpid()
    # print('root pid:', pid)
    current_process = psutil.Process(pid)
    mem = current_process.memory_info().rss
    root_pid_mem = mem / 1024 / 1024 / 1024
    for child in current_process.children(recursive=True):
        # print('pid', child.pid)
        mem += child.memory_info().rss
    # mem = mem * (psutil.virtual_memory().total / 1024/1024/1024) / 100
    mem = mem / 1024 / 1024 / 1024
    # print(mem)
    # print()
    # print(root_pid_mem)
    # print(sdg)
    return {"total": mem, "root_mem": root_pid_mem}


# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers_cache"
os.environ["NOUGAT_CHECKPOINT"] = "/tmp/nougat_checkpoint"
os.environ["NLTK_DATA"] = "/tmp/nltk_data"

args = json.load(open(os.environ["args_path"]))
args["BATCH_INDICE"] = int(os.environ.get("worker_id", 0))

logger = logging.getLogger()

logger.setLevel(logging.INFO)

logger.warning("Running locally")

# Online process triggered by S3 Object create event does not have batch indice
# Set default value for BATCH_INDICE if it doesn't exist
if "BATCH_INDICE" not in args:
    args["BATCH_INDICE"] = "0"
s3_bucket = args["S3_BUCKET"]
s3_prefix = args["S3_PREFIX"]
aosEndpoint = args["AOS_ENDPOINT"]

embeddingModelEndpoint = args["EMBEDDING_MODEL_ENDPOINT"]
etlModelEndpoint = args["ETL_MODEL_ENDPOINT"]
region = args["REGION"]
res_bucket = args["RES_BUCKET"]
offline = args["OFFLINE"]
qa_enhancement = args["QA_ENHANCEMENT"]
# TODO, pass the bucket and prefix need to handle in current job directly
batchIndice = args["BATCH_INDICE"]
processedObjectsTable = args["ProcessedObjectsTable"]
workspace_id = args["WORKSPACE_ID"]
workspace_table = args["WORKSPACE_TABLE"]

s3 = boto3.client("s3")
smr_client = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(processedObjectsTable)
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)

ENHANCE_CHUNK_SIZE = 25000
# Make it 3600s for debugging purpose
OBJECT_EXPIRY_TIME = 3600

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    "es",
    session_token=credentials.token,
)
MAX_OS_DOCS_PER_PUT = 8

# Set the NLTK data path to the /tmp directory for AWS Glue jobs
nltk.data.path.append("/tmp/nltk_data")

supported_file_types = ["pdf", "txt", "doc", "md", "html", "json", "jsonl", "csv"]


def decode_file_content(content: str, default_encoding: str = "utf-8"):
    """Decode the file content and auto detect the content encoding.

    Args:
        content: The content to detect the encoding.
        default_encoding: The default encoding to try to decode the content.
        timeout: The timeout in seconds for the encoding detection.
    """

    try:
        decoded_content = content.decode(default_encoding)
    except UnicodeDecodeError:
        # Try to detect encoding
        encoding = chardet.detect(content)["encoding"]
        decoded_content = content.decode(encoding)

    return decoded_content


# such glue job is running as map job, the batchIndice is the index per file to handle in current job
def iterate_s3_files(
    bucket: str, prefix: str, worker_num, batchIndice, max_file_num
) -> Generator:
    paginator = s3.get_paginator("list_objects_v2")
    currentIndice = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            currentIndice += 1

            if currentIndice > max_file_num:
                logger.info(
                    f"currentIndice: {currentIndice} reach max_file_num: {max_file_num}"
                )
                return
            key = obj["Key"]
            # skip the prefix with slash, which is the folder name
            if key.endswith("/"):
                continue
            logger.debug(
                "Current batchIndice: {}, bucket: {}, key: {}".format(
                    currentIndice, bucket, key
                )
            )
            #
            if (currentIndice - 1) % worker_num != int(batchIndice):
                logger.debug(
                    "currentIndice: {}, batchIndice: {}, skip file: {}".format(
                        currentIndice, batchIndice, key
                    )
                )
                continue
            logger.info(
                "Processing {} doc in {} batch, key: {}".format(
                    currentIndice, batchIndice, key
                )
            )
            file_type = key.split(".")[-1].lower()  # Extract file extension
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response["Body"].read()
            # assemble bucket and key as args for the callback function
            kwargs = {
                "bucket": bucket,
                "key": key,
                "etl_model_endpoint": etlModelEndpoint,
                "smr_client": smr_client,
                "res_bucket": res_bucket,
            }

            if file_type == "txt":
                yield "txt", decode_file_content(file_content), kwargs
            elif file_type == "csv":
                # Update row count here, the default row count is 1
                kwargs["csv_row_count"] = 1
                yield "csv", decode_file_content(file_content), kwargs
            elif file_type == "html":
                yield "html", decode_file_content(file_content), kwargs
            elif file_type in ["pdf"]:
                yield "pdf", file_content, kwargs
            elif file_type in ["jpg", "png"]:
                yield "image", file_content, kwargs
            elif file_type in ["docx", "doc"]:
                yield "doc", file_content, kwargs
            elif file_type == "md":
                yield "md", decode_file_content(file_content), kwargs
            elif file_type == "json":
                yield "json", decode_file_content(file_content), kwargs
            elif file_type == "jsonl":
                yield "jsonl", file_content, kwargs
            else:
                logger.info(f"Unknown file type: {file_type}")


def batch_generator(generator, batch_size: int):
    iterator = iter(generator)
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break
        yield batch


docsearch = None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
def aos_injection_helper(texts, dense_vecs_list, metadatas, index_name):
    global docsearch
    if docsearch is None:
        docsearch = OpenSearchVectorSearch(
            index_name=index_name,
            embedding_function=None,
            opensearch_url="https://{}".format(aosEndpoint),
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
    # # logger.info(
    #     "Adding documents %s to OpenSearch with index %s",
    #     document,
    #     index_name,
    # )
    # TODO: add endpoint name as a metadata of document
    OpenSearchVectorSearch.__add
    try:
        # TODO, consider the max retry and initial backoff inside helper.bulk operation instead of using original LangChain
        docsearch._OpenSearchVectorSearch__add(
            texts, embeddings=dense_vecs_list, metadatas=metadatas
        )
    except Exception as e:
        raise RuntimeError(f"Catch exception when adding document to OpenSearch: {e}")

    # docsearch.client.close()


def __aos_injection(texts, dense_vecs_list, metadatas, index_name):
    try:
        aos_injection_helper(texts, dense_vecs_list, metadatas, index_name)
    except:
        logger.error(traceback.format_exc())

    traceback.clear_frames(sys.exc_info()[2])
    # import gc
    # gc.collect()


# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
pendings = set()


def _aos_injection(
    documents: List[Document],
    index_name,
    aosEndpoint,
    endpoint_name=os.environ.get("embedding_endpoint_name", ""),
) -> Document:
    # If user customize the index, use the customized index as high priority, NOTE the custom index will be created with default AOS mapping in LangChain, use API to create the index with customized mapping before running the job if you want to customize the mapping
    assert isinstance(documents, list), type(documents)

    for document in documents:
        if "complete_heading" in document.metadata:
            document.page_content = (
                document.metadata["complete_heading"] + " " + document.page_content
            )
        else:
            document.page_content = document.page_content
        document.metadata["embedding_endpoint_name"] = endpoint_name
        save_content_to_s3(s3, document, res_bucket, SplittingType.CHUNK.value)

    texts = [doc.page_content for doc in documents]
    metadatas = [doc.metadata for doc in documents]

    # waiting
    # from concurrent.futures import wait, FIRST_COMPLETED
    # global pendings
    # while (len(pendings) > aos_injection_mp._max_workers) or \
    #     (psutil.virtual_memory().percent > 85 and len(pendings) > 2):
    #     used_momery = psutil.virtual_memory().used / 1024 / 1024 / 1024
    #     logger.info(f'waiting for aos_injection_mp, pendings num: {len(pendings)}, used mem: {used_momery}')
    #     _, pendings = wait(pendings, return_when=FIRST_COMPLETED)
    #     import gc
    #     gc.collect()
    #     time.sleep(5)

    embedding_execute_context = bge_m3_embedding_lock
    if embedding_execute_context is None:
        embedding_execute_context = contextlib.nullcontext()
    with embedding_execute_context:
        # import multiprocessing
        # logger.info(f'process: {multiprocessing.current_process().ident} enter embedding_execute_context')
        # time.sleep(4)
        logger.info(f"embedding documents num: {len(texts)}")
        embeddings = BGRM3Embedding().embed_documents(texts)

    dense_vecs_list = embeddings["dense_vecs_list"]
    colbert_vecs_list = embeddings["colbert_vecs_list"]

    colbert_vecs_lens = [len(colbert_vecs) for colbert_vecs in colbert_vecs_list]
    avg_lens = sum(colbert_vecs_lens) / len(colbert_vecs_lens)

    logger.info(
        f"avg_colbert_lens: {avg_lens}, colbert_vecs num: {len(colbert_vecs_lens)}"
    )

    # for doc_id, metadata in enumerate(metadatas):
    #         # lexical_weights = embeddings_vectors[0]["lexical_weights"][
    #         #     doc_id
    #         # ]
    #     colbert_vecs = colbert_vecs_list[doc_id]
    #     # embeddings_vectors_list.append(
    #     #     embeddings_vectors[0]["dense_vecs"][doc_id]
    #     # )
    #     metadata.update(
    #         {
    #             "additional_vecs": {
    #                 # "lexical_weights": lexical_weights,
    #                 "colbert_vecs": colbert_vecs,
    #             }
    #         }
    #     )

    # logger.info(f'aos_injection_mp._work_ids.qsize(): {aos_injection_mp._work_ids.qsize()}')

    # while aos_injection_mp._work_queue.qsize() > 2*aos_injection_mp._max_workers:
    #     logger.info(f"aos_injection_mp's _work_queue is full, qsize: {aos_injection_mp._work_queue.qsize()}, _max_workers: {aos_injection_mp._max_workers}, waiting... ")
    #     time.sleep(5)

    # pendings.add(
    #     aos_injection_mp.submit(
    #         __aos_injection,
    #         texts,
    #         dense_vecs_list,
    #         metadatas,
    #         index_name
    #     ))

    logger.info(f"put task, qsize: {aos_injection_task_queue.qsize()}")

    # for i in range(len(texts)):
    #     aos_injection_task_queue.put(
    #         {
    #             "texts":[texts[i]],
    #             "dense_vecs_list": [dense_vecs_list[i]],
    #             "metadatas": [metadatas[i]],
    #             "index_name": index_name
    #         }
    #     )

    for i in range(len(texts)):
        aos_injection_task_queue.put(
            {
                "text": texts[i],
                "embedding": dense_vecs_list[i],
                "metadata": metadatas[i],
                "index_name": index_name,
            }
        )

    mem = get_program_memory_usage()
    logger.info(
        f"current total memory usage: {mem['total']} GB, root pid: {mem['root_mem']} GB, pendings num: {len(pendings)}"
    )


# aos_injection_mp.submit(__aos_injection,texts,dense_vecs_list,metadatas,index_name)

# aos_injection_mp.submit(__aos_injection,texts,dense_vecs_list,metadatas,index_name)

# __aos_injection(texts,dense_vecs_list,metadatas,index_name)
# docsearch = OpenSearchVectorSearch(
#     index_name=index_name,
#     embedding_function=None,
#     opensearch_url="https://{}".format(aosEndpoint),
#     http_auth=awsauth,
#     use_ssl=True,
#     verify_certs=True,
#     connection_class=RequestsHttpConnection
# )


# # # logger.info(
# #     "Adding documents %s to OpenSearch with index %s",
# #     document,
# #     index_name,
# # )
# # TODO: add endpoint name as a metadata of document
# try:
#     # TODO, consider the max retry and initial backoff inside helper.bulk operation instead of using original LangChain
#     docsearch._OpenSearchVectorSearch__add(
#         texts,
#         embeddings=dense_vecs_list,
#         metadatas=metadatas
#     )
# except Exception as e:
#     logger.info(
#         f"Catch exception when adding document to OpenSearch: {e}"
#     )


def chunk_generator(
    content: List[Document], chunk_size: int = 500, chunk_overlap: int = 30
) -> Generator[Document, None, None]:
    temp_text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    temp_content = content
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    updated_heading_hierarchy = {}
    for temp_document in temp_content:
        temp_chunk_id = temp_document.metadata["chunk_id"]
        temp_split_size = len(temp_text_splitter.split_documents([temp_document]))
        # Add size in heading_hierarchy
        if "heading_hierarchy" in temp_document.metadata:
            temp_hierarchy = temp_document.metadata["heading_hierarchy"]
            temp_hierarchy["size"] = temp_split_size
            updated_heading_hierarchy[temp_chunk_id] = temp_hierarchy

    for document in content:
        splits = text_splitter.split_documents([document])
        # list of Document objects
        index = 1
        for split in splits:
            chunk_id = split.metadata["chunk_id"]
            logger.debug(chunk_id)
            split.metadata["chunk_id"] = f"{chunk_id}-{index}"
            if chunk_id in updated_heading_hierarchy:
                split.metadata["heading_hierarchy"] = updated_heading_hierarchy[
                    chunk_id
                ]
                logger.debug(split.metadata["heading_hierarchy"])
            index += 1
            yield split


def aos_injection(
    content: List[Document],
    embeddingModelEndpoint: str,
    aosEndpoint: str,
    index_name: str,
    file_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 30,
    gen_chunk: bool = True,
) -> List[Document]:
    """
    This function includes the following steps:
    1. split the document into chunks with chunk size to fit the embedding model, note the document is already splited by title/subtitle to form sementic chunks approximately;
    2. call the embedding model to get the embeddings for each chunk;
    3. call the AOS to index the chunk with the embeddings;
    Parameters:
    content (list): A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading hierarchy etc.
    embeddingModelEndpointList (List[str]): The endpoint list of the embedding model.
    aosEndpoint (str): The endpoint of the AOS.
    index_name (str): The name of the index to be created in the AOS.
    chunk_size (int): The size of each chunk to be indexed in the AOS.
    file_type (str): The file type of the document.
    gen_chunk (bool): Whether generate chunks or not.

    Returns:

    Note:
    """
    logger.debug(f"embeddingModelEndpoint: {embeddingModelEndpoint}")
    # embeddings = sm_utils.create_embeddings_with_m3_model(
    #     embeddingModelEndpoint, region, file_type
    # )

    if gen_chunk:
        generator = chunk_generator(
            content, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    else:
        generator = content

    batches = batch_generator(
        generator, batch_size=int(os.environ.get("embedding_chunk_num", 20))
    )
    # note: typeof(batch)->list[Document], sizeof(batches)=batch_size
    for batch in batches:
        if len(batch) == 0:
            continue
        _aos_injection(
            batch,
            # embeddings,
            index_name,
            aosEndpoint,
        )


def gen_documents(s3_bucket, s3_prefix, worker_num, batchIndice, max_file_num=math.inf):
    (
        embeddings_model_provider,
        embeddings_model_name,
        embeddings_model_dimensions,
        embeddings_model_type,
    ) = get_embedding_info(embeddingModelEndpoint)
    for file_type, file_content, kwargs in iterate_s3_files(
        s3_bucket, s3_prefix, worker_num, batchIndice, max_file_num=max_file_num
    ):
        try:
            res = cb_process_object(s3, file_type, file_content, **kwargs)
            for document in res:
                save_content_to_s3(
                    s3, document, res_bucket, SplittingType.SEMANTIC.value
                )
            # the res is unified to list[Doucment] type, store the res to S3 for observation
            # TODO, parse the metadata to embed with different index
            if res:
                logger.debug("Result: %s", res)

            open_search_index_type = "qq" if file_type == "jsonl" else "qd"

            aos_index = workspace_manager.update_workspace_open_search(
                workspace_id,
                embeddingModelEndpoint,
                embeddings_model_provider,
                embeddings_model_name,
                embeddings_model_dimensions,
                embeddings_model_type,
                ["zh"],
                open_search_index_type,
                # [file_type],
                # open_search_index_type
            )
            gen_chunk_flag = False if file_type == "csv" else True
            if file_type in supported_file_types:
                yield {
                    "aos_index": aos_index,
                    "gen_chunk_flag": gen_chunk_flag,
                    "documents": res,
                }
        except Exception as e:
            logger.error(
                "Error processing object %s: %s",
                kwargs["bucket"] + "/" + kwargs["key"],
                e,
            )
            traceback.print_exc()


def split_documents(
    documents_generator, chunk_size: int = 500, chunk_overlap: int = 30
):
    for document_dict in documents_generator:
        gen_chunk_flag = document_dict["gen_chunk_flag"]
        documents: list[Document] = document_dict["documents"]
        aos_index = document_dict["aos_index"]
        if gen_chunk_flag:
            generator = chunk_generator(
                documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        else:
            generator = iter(documents)

        for chunk in generator:
            yield {"document": chunk, "aos_index": aos_index}


# Main function to be called by Glue job script
def _main(worker_num, batchIndice, max_file_num=math.inf):
    logger.info("Starting Glue job with passing arguments: %s", args)
    logger.info("Running in offline mode with consideration for large file size...")
    # embeddings_model_provider, embeddings_model_name, embeddings_model_dimensions = (
    #     get_embedding_info(embeddingModelEndpoint)
    # )
    document_dicts = gen_documents(
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
        worker_num=worker_num,
        batchIndice=batchIndice,
        max_file_num=max_file_num,
    )
    chunk_dicts = split_documents(document_dicts)
    # print('list(chunk_dicts)',list(chunk_dicts))
    batches = batch_generator(
        chunk_dicts, batch_size=int(os.environ.get("embedding_chunk_num", 20))
    )

    for batch in batches:
        # print('batch: ',batch)
        if len(batch) == 0:
            continue
        index_name = batch[0]["aos_index"]
        documents = [i["document"] for i in batch]
        _aos_injection(
            documents,
            index_name,
            # embeddings,
            aosEndpoint,
        )


# Main function to be called by Glue job script
def __main(worker_num, batchIndice, max_file_num=math.inf):
    logger.info("Starting Glue job with passing arguments: %s", args)
    logger.info("Running in offline mode with consideration for large file size...")
    embeddings_model_provider, embeddings_model_name, embeddings_model_dimensions = (
        get_embedding_info(embeddingModelEndpoint)
    )
    for file_type, file_content, kwargs in iterate_s3_files(
        s3_bucket, s3_prefix, worker_num, batchIndice, max_file_num=max_file_num
    ):
        try:
            res = cb_process_object(s3, file_type, file_content, **kwargs)
            for document in res:
                save_content_to_s3(
                    s3, document, res_bucket, SplittingType.SEMANTIC.value
                )

            # the res is unified to list[Doucment] type, store the res to S3 for observation
            # TODO, parse the metadata to embed with different index
            if res:
                logger.debug("Result: %s", res)

            aos_index = workspace_manager.update_workspace_open_search(
                workspace_id,
                embeddingModelEndpoint,
                embeddings_model_provider,
                embeddings_model_name,
                embeddings_model_dimensions,
                ["zh"],
                [file_type],
            )

            gen_chunk_flag = False if file_type == "csv" else True
            if file_type in supported_file_types:
                aos_injection(
                    res,
                    embeddingModelEndpoint,
                    aosEndpoint,
                    aos_index,
                    file_type,
                    gen_chunk=gen_chunk_flag,
                )

            if qa_enhancement == "true":
                enhanced_prompt_list = []
                # iterate the document to get the QA pairs
                for document in res:
                    # Define your prompt or else it uses default prompt
                    prompt = ""
                    # Make sure the document is Document object
                    logger.debug(
                        "Enhancing document type: {} and content: {}".format(
                            type(document), document
                        )
                    )
                    ewb = EnhanceWithBedrock(prompt, document)
                    # This is should be optional for the user to choose the chunk size
                    document_list = ewb.SplitDocumentByTokenNum(
                        document, ENHANCE_CHUNK_SIZE
                    )
                    for document in document_list:
                        enhanced_prompt_list = ewb.EnhanceWithClaude(
                            prompt, document, enhanced_prompt_list
                        )
                    logger.debug(f"Enhanced prompt: {enhanced_prompt_list}")

                if len(enhanced_prompt_list) > 0:
                    for document in enhanced_prompt_list:
                        save_content_to_s3(
                            s3,
                            document,
                            res_bucket,
                            SplittingType.QA_ENHANCEMENT.value,
                        )
                    aos_injection(
                        enhanced_prompt_list,
                        embeddingModelEndpoint,
                        aosEndpoint,
                        aos_index,
                        "qa",
                    )

        except Exception as e:
            logger.error(
                "Error processing object %s: %s",
                kwargs["bucket"] + "/" + kwargs["key"],
                e,
            )
            traceback.print_exc()


def main(worker_num, batchIndice, max_file_num=math.inf):
    logger.debug("boto3 version: %s", boto3.__version__)
    # worker_num = int(os.environ.get('worker_num',1))
    logger.info(f"worker: {batchIndice}/{worker_num} starting")

    # Set the NLTK data path to the /tmp directory for AWS Glue jobs
    nltk.data.path.append("/tmp")
    # List of NLTK packages to download
    nltk_packages = ["words", "punkt"]
    # Download the required NLTK packages to /tmp
    for package in nltk_packages:
        # Download the package to /tmp/nltk_data
        nltk.download(package, download_dir="/tmp/nltk_data")

    _main(worker_num, batchIndice, max_file_num=max_file_num)


# def main_multithread():
#     global  bge_m3_embedding_lock, aos_injection_mp
#     bge_m3_embedding_lock = threading.Lock()
#     aos_injection_mp =  ProcessPoolExecutor(int(os.environ.get('aos_worker_num',10)))
#     logger.info(f'aos_injection_mp: {aos_injection_mp._max_workers}')
#     main()


# def main_profile():
#     from line_profiler import LineProfiler
#     profile = LineProfiler()
#     profile.add_function(_main)
#     profile.add_function(iterate_s3_files)
#     profile.add_function(aos_injection)
#     profile.add_function(_aos_injection)
#     lp_wrapper = profile(main)
#     lp_wrapper(1,0,10)
#     profile.print_stats()


if __name__ == "__main__":
    pass
    # main()
    # main_profile()
    # logger.info("boto3 version: %s", boto3.__version__)
    # worker_num = int(os.environ.get('worker_num',1))
    # logger.info(f'worker: {args["BATCH_INDICE"]}/{worker_num} starting')

    # # Set the NLTK data path to the /tmp directory for AWS Glue jobs
    # nltk.data.path.append("/tmp")
    # # List of NLTK packages to download
    # nltk_packages = ["words", "punkt"]
    # # Download the required NLTK packages to /tmp
    # for package in nltk_packages:
    #     # Download the package to /tmp/nltk_data
    #     nltk.download(package, download_dir="/tmp/nltk_data")

    # main(worker_num)

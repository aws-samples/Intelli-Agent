import os
import json
import logging
import time
import boto3
import requests
import json
import itertools
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn

from tenacity import retry, stop_after_attempt, wait_exponential
from itertools import product
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from requests_aws4auth import AWS4Auth
from opensearchpy import RequestsHttpConnection

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.document_loaders import UnstructuredMarkdownLoader
from langchain.vectorstores import OpenSearchVectorSearch
from langchain.evaluation import load_evaluator, EvaluatorType
from langchain.llms.bedrock import Bedrock
# from langchain_core.language_models import BaseLanguageModel

from llm_bot_dep.loaders.nougat_pdf import NougatPDFLoader
from llm_bot_dep.loaders.markdown import process_md, CustomMarkdownLoader
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter
from llm_bot_dep.sm_utils import create_sagemaker_embeddings_from_js_model, SagemakerEndpointVectorOrCross

from ragas.testset import TestsetGenerator
from langchain.chat_models import ChatOpenAI
from ragas.llms import LangchainLLM

from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# set logger level to debug
logger.setLevel(logging.INFO)

AOS_API_SUFFIX = "aos"
LLM_API_SUFFIX = "llm"
embeddingModelEndpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
aosEndpoint = os.getenv("AOS_ENDPOINT")
region = os.getenv("REGION")
apiEndpoint = os.getenv("APIEndpointAddress")
openaiApiKey = os.getenv("OPENAI_API_KEY")
openaiApiBase = os.getenv("OPENAI_API_BASE")

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

default_aos_index_name = "llm-bot-index"

s3 = boto3.client("s3")
glue = boto3.client('glue')

metadata_template = {
    "content_type": "paragraph",
    "current_heading": 0,
    "heading_hierarchy": {},    
    "figure_list": [],
    "chunk_id": "$$",
    "file_path": "",
    "keywords": [],
    "summary": "",
}

# prerequisite for testdata generation using ragas, or using OpenAIEmbeddings but need to set the OPENAI_API_KEY/OPENAI_API_BASE in env
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
bedrock_llm = Bedrock(
    model_id = "anthropic.claude-v2:1", 
    client = bedrock_client,
    model_kwargs = {'temperature': 0}
)
_bedrock_embedding = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
    # model_id="cohere.embed-multilingual-v3", region_name="us-east-1"
    # model_id = "amazon.titan-text-express-v1", region_name="us-east-1"
)

def csdc_markdown_loader(file_path: str) -> List[Document]:
    # read content from file_path
    with open(file_path, "r") as f:
        file_content = f.read()
    # placeholder for bucket and key
    bucket = "default"
    key = "default"

    loader = CustomMarkdownLoader(aws_path=f"s3://{bucket}/{key}")
    docs = loader.load(file_content)
    logger.debug("csdc markdown load data: {}".format(docs))
    return docs

def nougat_loader(file_path: str) -> List[Document]:
    loader = NougatPDFLoader(file_path)
    docs = loader.load()
    logger.debug("nougat load data: {}".format(docs))

def llamaIndex_pdf_loader(file_path: str) -> List[Document]:
    try:
        import pypdf
    except ImportError:
        raise ImportError(
            "pypdf is required to read PDF files: `pip install pypdf`"
        )
    with open(file_path, "rb") as fp:
        # Create a PDF object
        pdf = pypdf.PdfReader(fp)

        # Get the number of pages in the PDF document
        num_pages = len(pdf.pages)

        # Iterate over every page
        docs = []
        for page in range(num_pages):
            # Extract the text from the page
            page_text = pdf.pages[page].extract_text()
            page_label = pdf.page_labels[page]

            metadata = {"page_label": page_label, "file_name": file_path}
            logger.debug("page_text: {}, page_label: {}".format(page_text, page_label))
            docs.append(Document(page_content=page_text, metadata=metadata))

def langchain_md_loader(file_path: str) -> List[Document]:
    loader = UnstructuredMarkdownLoader(file_path, mode="elements")
    docs = loader.load()
    logger.debug("langchain md load data: {}".format(docs))
    return docs

def langchain_unstructured_loader(file_path: str) -> List[Document]:
    """
    Loads a document from a file path.

    Args:
        file_path (str): The path to the file.

    Returns:
        list[Document]: A list of Document objects.
    """
    loader = UnstructuredFileLoader(file_path, mode="elements")
    docs = loader.load()
    logger.info("unstructured load data: {}".format(docs))
    return docs

def parse_log_to_document_list(log_content: str) -> List[Document]:
    # Split the log content into page content and metadata parts
    parts = log_content.split("Metadata: ")
    page_content = parts[0].replace("Page Content: ", "").strip()
    metadata = json.loads(parts[1].strip()) if len(parts) > 1 else {}

    # Create a Document object
    doc = Document(page_content=page_content, metadata=metadata)
    return [doc]

def csdc_unstructured_loader(file_path: str) -> List[Document]:
    """
    Loads a document from a file path.

    Args:
        file_path (str): The path to the file.

    Returns:
        list[Document]: A list of Document objects.
    """
    """
    Such function include serveral steps to interact with solution deployed on AWS.
    1. upload the file to s3 bucket, we use the DocumentBucket from cdk output, the whole s3 path is s3://<DocumentBucket>/demo/pdf-sample-01.pdf, pdf-sample-01 is the file name
    2. trigger the offline etl job with api, we use the apiEndpoint from cdk output, the payload is {
        "s3Bucket": "<DocumentBucket>",
        "s3Prefix": "demo",
        "aosIndex": "demo",
        "qaEnhance": "false",
        "offline": "true"
    }
    3. check the glue job status and wait for the job to finish with success status
    4. fetch loaded files from s3 bucket, we use the ChunkBucket from cdk output, the whole s3 path is s3://<ChunkBucket>/pdf-sample-01/before-splitting/<%Y-%m-%d-%H>/<datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')>.log, pdf-sample-01 is the file name
    """
    # first get DocumentBucket and ChunkBucket from env variables
    document_bucket = os.getenv("DocumentBucket")
    chunk_bucket = os.getenv("ChunkBucket")

    # step 1, upload the file to s3 bucket with fixed s3 prefix demo/<file name>
    # extract file name also in consideration of file name with blank space
    file_name = str(os.path.basename(file_path))
    # make the s3 prefix unique
    s3_prefix = "demo/" + file_name
    # upload the file to s3 bucket
    s3.upload_file(file_path, document_bucket, s3_prefix)

    # step 2, trigger the offline etl job with api
    # construct the payload
    payload = json.dumps({
        "s3Bucket": document_bucket,
        "s3Prefix": s3_prefix,
        "aosIndex": "demo",
        "qaEnhance": "false",
        "offline": "true"
    })
    headers = {'Content-Type': 'application/json'}
    logger.debug("payload: {}, apiEndpoint: {}, headers: {}, type: {}".format(payload, apiEndpoint, headers, type(payload)))
    try:
        response = requests.request("POST", apiEndpoint + 'etl', headers=headers, data=payload)
        logger.info("response: {}".format(json.loads(response.text)))
    except Exception as e:
        logger.error("error: {}".format(e))
        raise e

    # step 3, check the glue job status and wait for the job to finish with success status
    # load the job name from environment variable and convert it to string like 'PythonShellJobB6964098-YYlLj16uCsAn'
    glue_job_name = str(os.getenv('GLUE_JOB_NAME'))
    # sleep 10 seconds to wait for the glue job to start
    time.sleep(10)
    # check the glue job status and wait for the job to finish with success status
    response = glue.get_job_runs(JobName=glue_job_name, MaxResults=10)
    # function only return running aws glue jobs
    job_runs = [job_run for job_run in response['JobRuns'] if job_run['JobRunState'] == 'RUNNING']
    while len(job_runs) > 0:
        time.sleep(10)
        logger.info("waiting for glue job to finish...")
        response = glue.get_job_runs(JobName=glue_job_name, MaxResults=10)
        job_runs = [job_run for job_run in response['JobRuns'] if job_run['JobRunState'] == 'RUNNING']

    # step 4, fetch loaded files from s3 bucket
    # scan the ChunkBucket s3://<ChunkBucket>/pdf-sample-01/before-splitting/
    # construct the s3 prefix, note to strip the file type
    s3_prefix = file_name.split('.')[0] + "/before-splitting/"
    logger.info("s3_prefix: {}, chunk_bucket: {}".format(s3_prefix, chunk_bucket))
    # find the latest timestamp folder then fetch the latest log file under that folder
    response = s3.list_objects_v2(Bucket=chunk_bucket, Prefix=s3_prefix)
    logger.info("list_objects_v2 response: {}".format(response))
    # get the latest timestamp folder
    latest_timestamp = max([content['Key'].split('/')[-2] for content in response['Contents']])
    # construct the s3 prefix with latest timestamp folder
    s3_prefix = s3_prefix + latest_timestamp + "/"
    # find the latest log file
    response = s3.list_objects_v2(Bucket=chunk_bucket, Prefix=s3_prefix)
    logger.info("list_objects_v2 response: {}".format(response))
    latest_log_file = max([content['Key'].split('/')[-1] for content in response['Contents']])
    # construct the s3 prefix with latest log file
    s3_prefix = s3_prefix + latest_log_file
    # download the log file to local
    s3.download_file(chunk_bucket, s3_prefix, file_name + ".log")

    # read content from file_path
    with open(file_name + ".log", "r") as f:
        file_content = f.read()
        logger.debug("file_content: {}".format(file_content))
    
    # transform to Document object
    doc = parse_log_to_document_list(file_content)
    logger.info("csdc unstructured load data: {} and type: {}".format(doc, type(doc)))
    # return to raw extracted file contents to match with the function as any loader class. TODO: return the result of splitter (SplittingType.SEMANTIC) to integrate into current benchmark
    return doc

def langchain_recursive_splitter(docs: List[Document]) -> List[Document]:
    """
    Splits a document into chunks recursively.

    Args:
        docs (list[Document]): A list of Document objects.
        
    Returns:
        list[Document]: A list of Document objects.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap  = 30,
        length_function = len,
        add_start_index = True,
    )
    docs = text_splitter.split_documents(docs)
    logger.debug("langchain recursive splitter: {}".format(docs))
    return docs

def csdc_markdown_header_splitter(docs: List[Document]) -> List[Document]:
    """
    Splits a document into chunks recursively.

    Args:
        docs (list[Document]): A list of Document objects.

    Returns:
        list[Document]: A list of Document objects.
    """
    doc_list = []
    for doc in docs:
        # Split the document into chunks based on the headers
        markdown_splitter = MarkdownHeaderTextSplitter("default")
        docs = markdown_splitter.split_text(doc)
        logger.debug("csdc markdown header splitter: {}".format(docs))
        doc_list.extend(docs)
    return doc_list

def documents_to_strings(documents: List[Document]) -> List[str]:
    serialized_documents = []
    for doc in documents:
        # Serialize the document into a JSON string
        serialized_doc = json.dumps({
            'page_content': doc.page_content,
            'metadata': doc.metadata,
            'type': doc.type
        })
        serialized_documents.append(serialized_doc)
    return serialized_documents

def openai_embedding(index: str, docs: List[Document]) -> List[List[float]]:
    embeddings = OpenAIEmbeddings()
    docs = documents_to_strings(docs)
    embeddings.embed_documents(docs)
    logger.debug("openai embeddings: {}".format(embeddings))
    return embeddings

def csdc_embedding(index: str, docs: List[Document]) -> List[List[str]]:
    # embedding
    batches = batch_generator(docs, batch_size=5)
    for batch in batches:
        for doc in batch:
            embedding_res = _csdc_embedding(default_aos_index_name, doc)

def _csdc_embedding(index: str, doc: Document):
    """
    Embeds the given documents using the CSDC embedding model.

    Args:
        index (str): The name of the index to which the documents will be added.
        document (Document): The document to embed.

    Returns:
        document_id (str): The ID of the document in the index.
        e.g. 
        "document_id": [
            "05d0f6bb-b5c6-40e0-8064-c79448bd2332"
        ]
    """
    page_content = doc.page_content
    metadata = doc.metadata
    payload = json.dumps({
        "aos_index": index,
        "operation": "embed_document",
        "body": {
            "documents": {
                "page_content": page_content,
                "metadata": metadata
            }
        }
    })
    headers = {'Content-Type': 'application/json'}
    logger.debug("payload: {}, apiEndpoint: {}, headers: {}, type: {}".format(payload, apiEndpoint, headers, type(payload)))
    try: 
        response = requests.request("POST", apiEndpoint + 'aos', headers=headers, data=payload)
        logger.info("csdc embedding: {}".format(json.loads(response.text)))
        return json.loads(response.text)
    except Exception as e:
        logger.error("error: {}".format(e))
        raise e

def bedrock_embedding(index: str, docs: List[Document]) -> List[List[str]]:
    """
    Embeds the given documents using the Bedrock embedding model.

    Args:
        index (str): The name of the index to which the documents will be added.
        document (Document): The document to embed.

    Returns:
        list: List of ids from adding the texts into the vectorstore.
    """
    opensearch_vector_search = OpenSearchVectorSearch(
        opensearch_url="https://localhost:9200",
        index_name=index,
        embedding_function=_bedrock_embedding,
        http_auth=("admin", "admin"),
        use_ssl = False,
        verify_certs = False,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
        bulk_size = 1024,
    )
    res_list = []
    batches = batch_generator(docs, batch_size=5)
    for batch in batches:
        for doc in batch:
            res = opensearch_vector_search.add_embeddings(
                text_embeddings = [(doc.page_content, _bedrock_embedding.embed_documents([doc.page_content])[0])],
                metadatas = None,
                ids = None,
                bulk_size = 1024,
            )
            res_list.append(res)
    logger.debug("bedrock embedding: {}".format(res_list))
    return res_list

def _query_embedding(index: str = default_aos_index_name, query: str = "Hello World") -> List[float] :
    """
    Embeds the given query using the CSDC embedding model.

    Args:
        index (str): The name of the index to which the documents will be added, not used for now.
        query (str): The query to embed.

    Returns:
        list: A list of floats with length of vector dimensions (1024).
    """
    headersList = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "aos_index": index,
        "operation": "embed_query",
        "body": {
            "query": query
        }
    })

    try:
        response = requests.request("POST", apiEndpoint + AOS_API_SUFFIX, data=payload, headers=headersList)
        logger.info("response: {}".format(json.loads(response.text)))
    except Exception as e:
        logger.error("error: {}".format(e))
        raise e
    return response

def aos_retriever(index: str, query: str, size: int = 10):
    # such aos running inside vpc created by solution template, we use request library to call the api backed by api gw & lambda
    query_res = _query_embedding(index, query)
    vector_field = json.loads(query_res.text)
    headersList = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    logger.info("vector_field: {} and type: {}".format(vector_field, type(vector_field)))
    payload = json.dumps({
        "aos_index": index,
        "operation": "query_knn",
        "body": {
            "query": vector_field,
            "size": size,
        }
    })

    try:
        response = requests.request("GET", apiEndpoint + AOS_API_SUFFIX, data=payload, headers=headersList)
        # parse the response and get the query result
        response = json.loads(response.text)
        logger.info("aos retriever response: {}".format(response))
        # parse the response to get the score with following schema
        """
        {
            "took": 2,
            "timed_out": false,
            "_shards": {
                "total": 5,
                "successful": 5,
                "skipped": 0,
                "failed": 0
            },
            "hits": {
                "total": {
                "value": 111,
                "relation": "eq"
                },
                "max_score": 0.45040068,
                "hits": [
                {
                    "_index": "jsonl",
                    "_id": "df050ddf-98c2-4396-83e2-ce467164b440",
                    "_score": 0.45040068,
                    ...
        """
        score_list = [float(score['_score']) for score in response['hits']['hits']]
        # assemble the response with type as [(Document, score), (Document, score), ...], (hit['_source']['text']) is the document page_content
        response = [(Document(page_content=hit['_source']['text']), score) for hit, score in zip(response['hits']['hits'], score_list)]
            
    except Exception as e:
        logger.error("error: {}".format(e))
        raise e
    return response

def local_aos_retriever(index: str, query: str, size: int = 10) -> List[Tuple[Document, float]]:
    """
    retrieve the similar documents with query from local aos

    Args:
        index (str): The name of the index to which the documents will be added.
        query (str): The query to embed.
        size (int): The number of documents to retrieve.

    Returns:
        list: A list of tuples with document and score, e.g. [(Document, float), (Document, float), ...]
    """
    # assure local aos is running, e.g. simplely using 'docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" opensearchproject/opensearch:latest'
    opensearch_vector_search = OpenSearchVectorSearch(
        opensearch_url="https://localhost:9200",
        index_name=index,
        embedding_function=_bedrock_embedding,
        http_auth=("admin", "admin"),
        use_ssl = False,
        verify_certs = False,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
        bulk_size = 1024,
    )
    response = opensearch_vector_search.similarity_search_with_score(query, k=size)
    logger.info("local aos retriever response: {}".format(response))
    # parse the response to get the score with type List[Tuple[Document, float]]
    score_list = [float(score[1]) for score in response]
    return response 

# utils to run embeddings with metrics of dimension and time
def run_embeddings(embeddings_list, docs: List[str]):
    results = []
    for embed_func in embeddings_list:
        start = time.perf_counter()
        embedding_result = embed_func.embed_documents(docs)
        end = time.perf_counter()
        time_elapsed = end - start
        results.append({
            'Model': embed_func.__class__.__name__,
            'Dimensions': len(embedding_result[0]),
            'time': round(time_elapsed, 4)
        })
    return results

def faiss_retriver(texts: List[str], query: str):
    retriever = FAISS.from_texts(texts, OpenAIEmbeddings()).as_retriever()
    docs = retriever.get_relevant_documents(query)
    logger.debug("retriever docs: {}".format(docs))
    db = FAISS.from_texts(texts, OpenAIEmbeddings())
    docs_with_score = db.similarity_search_with_score(query, 3)
    logger.debug("docs_with_score: {}".format(docs_with_score))
    return docs_with_score

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def langchain_evaluator(prediction: str, reference: str, type: str):
    """
    evaluate the retrieved documents with query and return summary result depend on the type of evaluator

    Args:
        prediction (str): The query to evaluate.
        reference (str): The reference to evaluate.
        type (str): The type of evaluator to use.
    
    Returns:
        dict: A dictionary of evaluation results, e.g. {'score': 0.1682955026626587}
    """
    # explicitly set the llm model for bedrock
    bedrock_llm = Bedrock(
        model_id = "anthropic.claude-v2:1", 
        client = bedrock_client,
        model_kwargs = {'temperature': 0}
    )
    evaluator = load_evaluator(type, llm=bedrock_llm)
    response = evaluator.evaluate_strings(prediction=prediction, reference=reference)
    logger.debug("evaluator response: {}".format(response))
    return response

def llama_index_evalutor(query: str, docs_with_score: List[Tuple[str, float]]):
    pass

def testdata_generate(doc: Document, llm: str = "bedrock", embedding: str = "bedrock", test_size: int = 3):
    """
    generate test data for evaluation
    """
    if llm == "bedrock":
        generator_llm = LangchainLLM(llm=bedrock_llm)
        critic_llm = LangchainLLM(llm=bedrock_llm)
    elif llm == "openai":
        generator_llm = LangchainLLM(llm=ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openaiApiKey, openai_api_base=openaiApiBase))
        critic_llm = LangchainLLM(llm=ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openaiApiKey, openai_api_base=openaiApiBase))
        # critic_llm = LangchainLLM(llm=ChatOpenAI(model="gpt-4"))
    else:
        raise ValueError(f"Unsupported llm: {llm}")

    # check embedding model
    if embedding == "bedrock":
        embeddings_model = bedrock_embedding
    elif embedding == "openai":
        embeddings_model = OpenAIEmbeddings()

    # Change resulting question type distribution
    testset_distribution = {
        "simple": 0.25,
        "reasoning": 0.5,
        "multi_context": 0.0,
        "conditional": 0.25,
    }

    # percentage of conversational question
    chat_qa = 0.2

    test_generator = TestsetGenerator(
        generator_llm=generator_llm,
        critic_llm=critic_llm,
        embeddings_model=embeddings_model,
        testset_distribution=testset_distribution,
        chat_qa=chat_qa,
    )

    testset = test_generator.generate(doc, test_size=test_size)
    test_df = testset.to_pandas()
    logger.debug("testdata head: {}".format(test_df.head()))

    # Saving to a csv and txt file for debugging purpose
    test_df.to_csv('test_data.csv', index=False)
    test_df.to_csv('test_data.txt', sep='\t', index=False)
    
    # extract the question and answer from testset
    question = test_df['question'].tolist()
    question_type = test_df['question_type'].tolist()

    return question, question_type

class WorkflowExecutor:
    """
    A class to execute a workflow with various components such as loaders, splitters,
    embedders, retrievers, and evaluators.

    Attributes:
        components (dict): A dictionary to store lists of different workflow components.
    """
    def __init__(self):
        """Initializes the WorkflowExecutor with empty lists of components."""
        self.components = {
            'loaders': [],
            'splitters': [],
            'embedders': [],
            'retrievers': [],
            'evaluators': []
        }

        self.index = default_aos_index_name
        self.size = 10

    def update_component(self, component_type, component, action):
        """
        Adds or removes a component to/from the respective component list.

        Args:
            component_type (str): The type of component (e.g., 'loaders', 'splitters').
            component (object): The component to add or remove.
            action (str): 'add' to add the component, 'remove' to remove it.

        Raises:
            ValueError: If the component type is invalid.
        """
        if component_type in self.components:
            if action == 'add':
                self.components[component_type].append(component)
            elif action == 'remove' and component in self.components[component_type]:
                self.components[component_type].remove(component)
        else:
            raise ValueError(f"Invalid component type: {component_type}")

    def execute_workflow(self, doc_path: str, query, skip: bool = False):
        """
        Executes the workflow with all combinations of components and returns the results.

        Args:
            doc_path (str): The path to the document to be loaded.
            query (str): The query for retrieval and evaluation.

        Returns:
            list: A list of results from executing each workflow combination.

        Embedding evaluation: embedding into AOS using solution and langchain with different index , then using same question to query the retrieved references, calculate the similarities score between query and retrieved score, compare the score for both methods.

        E2E LLM evaluation: construct dataset with ground truth and using exiting langchain or llama index library to evaluate the faithfulness, relevance and accuracy metrics, OpenAI or Claude will be used as judger to determine the final score.
        """
        summary = {
            'rounds_of_experiments': 0,
            'number_of_evaluation_questions': len(query),
            'chunk_size': None,  # Update this if you have chunk size information
            'overlap_size': None, # Update this if you have overlap size information
            'load_method': [],
            'split_method': [],
            'retrieval_method': [],
            'embedding_algorithm_model': [],
            'number_of_chunks_retrieved': 0,
            'average_relevance_score': 0,
            'average_similarity_score': 0,
            'average_time_of_retrieval': 0
        }

        total_relevance_score = 0
        total_similarity_score = 0
        total_retrieval_time = 0

        # results_matrix = []
        for loader, splitter, embedder, retriever, evaluator in product(
            self.components['loaders'],
            self.components['splitters'],
            self.components['embedders'],
            self.components['retrievers'],
            self.components['evaluators']
        ):
            start_time = time.perf_counter()
            loader_res = loader(doc_path)

            if not skip:
                # Execute splitter and embedder if flag is not set to skip
                splitter_res = splitter(loader_res)
                embed_res = embedder(self.index, splitter_res)
                summary['split_method'].append(splitter.__name__)
                summary['embedding_algorithm_model'].append(embedder.__name__)
            else:
                # Skip splitter and embedder steps
                logger.info("Skip splitter and embedder steps")
                summary['split_method'].append("Skipped")
                summary['embedding_algorithm_model'].append("Skipped")

            retriever_res = retriever(self.index, query, self.size)
            retrieval_time = time.perf_counter() - start_time

            total_retrieval_time += retrieval_time
            summary['rounds_of_experiments'] += 1
            summary['load_method'].append(loader.__name__)
            summary['split_method'].append(splitter.__name__)
            summary['retrieval_method'].append(retriever.__name__)
            summary['embedding_algorithm_model'].append(embedder.__name__)
            summary['number_of_chunks_retrieved'] += len(retriever_res)

        #  openai required for now, bedrock is not working even setup the llm model explicitly
            for reference in retriever_res:
                logger.info("reference: {} with type {}".format(reference, type(reference)))
                score = evaluator(prediction=query, reference=reference[0].page_content, type=EvaluatorType.EMBEDDING_DISTANCE)['score']
                total_similarity_score += score
                # TODO, unified score parse method
                total_relevance_score += float(reference[1])
                # total_relevance_score += float(score['_score']) for score in reference['hits']['hits'] for csdc

                # results_matrix.append(evaluator(prediction=query, reference=reference.page_content, type=EvaluatorType.EMBEDDING_DISTANCE)['score'])
        summary['average_relevance_score'] = total_relevance_score / summary['number_of_chunks_retrieved']
        summary['average_similarity_score'] = total_similarity_score / summary['number_of_chunks_retrieved']
        summary['average_time_of_retrieval'] = total_retrieval_time / summary['rounds_of_experiments']

        return summary

    def summary_viz(self, summary: List[Dict[str, Any]]):
        """
        Visualizes the summary data to gain insights on the best combination for relevance and retrieval score.

        Args:
            summary (list): Rounds of experiments with metrics of relevance and retrieval score.

        Returns:
            Display the bar charts of average relevance and retrieval score sperately with x axis as rounds of experiments and y axis as average score and similarity score.
        """
       # Convert the data to a DataFrame
        df = pd.DataFrame(summary)

        # Plotting
        plt.figure(figsize=(12, 6))

        # Plotting average_relevance_score and average_similarity_score as separate bar charts
        plt.subplot(1, 2, 1)
        seaborn.barplot(x='rounds_of_experiments', y='average_relevance_score', data=df, color='blue')
        plt.title('Average Relevance Score per Round')
        plt.xlabel('Rounds of Experiments')
        plt.ylabel('Average Relevance Score')

        plt.subplot(1, 2, 2)
        seaborn.barplot(x='rounds_of_experiments', y='average_similarity_score', data=df, color='red')
        plt.title('Average Similarity Score per Round')
        plt.xlabel('Rounds of Experiments')
        plt.ylabel('Average Similarity Score')

        plt.tight_layout()
        plt.show()

# Preparing loader, splitter, and embeddings retriever list, iterate them to create comparasion matrix
loader_list = [langchain_unstructured_loader, nougat_loader, csdc_markdown_loader]
splitter_list = [langchain_recursive_splitter, csdc_markdown_header_splitter]
embeddings_list = [openai_embedding, csdc_embedding]
retriever_list = [faiss_retriver, aos_retriever, local_aos_retriever]
evalutor_list = [langchain_evaluator]

def batch_generator(generator, batch_size: int):
    iterator = iter(generator)
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break
        yield batch

# Debugging purpose
if __name__ == "__main__":
    """
    evaluate the retrieved documents with query and return summary result including metrics below:
    1. # round of experiments
    2. # of evaluation questions
    3. chunk size and overlap size
    4. split method
    5. retrieval method
    6. embedding algorithm & model
    7. # of chunks retrieved
    8. average relevance score of retrival
    9. average similarity score of retrival
    10. average time of retrival
    """
    # initialization of workflow executor
    legacy = WorkflowExecutor()
    legacy.update_component('loaders', langchain_unstructured_loader, 'add')
    legacy.update_component('splitters', langchain_recursive_splitter, 'add')
    legacy.update_component('embedders', bedrock_embedding, 'add')
    legacy.update_component('retrievers', local_aos_retriever, 'add')
    legacy.update_component('evaluators', langchain_evaluator, 'add')
    # response = legacy.execute_workflow("pdf-sample-01.pdf", "请介绍什么是kindle以及它的主要功能？")
    # logger.info("test of legacy workflow: {}".format(response))

    loader_res = langchain_unstructured_loader("pdf-sample-01-eng.pdf")
    question_list, question_type_list = testdata_generate(loader_res, llm="bedrock", embedding="bedrock", test_size=2)
    
    # iterate the question list to execute the workflow
    response_list = []
    for question in question_list:
        response = legacy.execute_workflow("pdf-sample-01-eng.pdf", question)
        logger.info("test of legacy workflow: {}".format(response))
        response_list.append(response)

    logger.info("response_list: {}".format(response_list))

    # visualize the summary
    legacy.summary_viz(response_list)

    # csdc = WorkflowExecutor()
    # csdc.update_component('loaders', csdc_unstructured_loader, 'add')
    # csdc.update_component('splitters', csdc_markdown_header_splitter, 'add')
    # csdc.update_component('embedders', csdc_embedding, 'add')
    # csdc.update_component('retrievers', aos_retriever, 'add')
    # csdc.update_component('evaluators', langchain_evaluator, 'add')
    # response = csdc.execute_workflow("md-sample-01.md", "请介绍什么是kindle以及它的主要功能？", skip=True)
    # logger.info("test of csdc workflow: {}".format(response))
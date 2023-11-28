import os
import json
import logging
import time
import boto3
import requests
import json

from tenacity import retry, stop_after_attempt
from itertools import product
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from requests_aws4auth import AWS4Auth
from opensearchpy import RequestsHttpConnection

from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.vectorstores import OpenSearchVectorSearch

from llm_bot_dep.loaders.nougat_pdf import NougatPDFLoader
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter
from llm_bot_dep.sm_utils import create_sagemaker_embeddings_from_js_model, SagemakerEndpointVectorOrCross

from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

embeddingModelEndpoint = os.getenv("EMBEDDING_MODEL_ENDPOINT")
aosEndpoint = os.getenv("AOS_ENDPOINT")
region = os.getenv("REGION")
apiEndpoint = os.getenv("APIEndpointAddress")

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

default_aos_index_name = "llm-bot-index"

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

def nougat_loader(file_path: str) -> List[Document]:
    loader = NougatPDFLoader(file_path)
    docs = loader.load()
    logger.info("nougat load data: {}".format(docs))

def llamaIndex_loader(file_path: str) -> List[Document]:
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
            logger.info("page_text: {}, page_label: {}".format(page_text, page_label))
            docs.append(Document(page_content=page_text, metadata=metadata))
        
def unstructured_loader(file_path: str) -> List[Document]:
    loader = UnstructuredFileLoader(file_path, mode="elements")
    docs = loader.load()
    logger.info("unstructured load data: {}".format(docs))
    return docs

def recursive_splitter(docs: List[Document]) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap  = 30,
        length_function = len,
        add_start_index = True,
    )
    docs = text_splitter.split_documents(docs)
    logger.info("langchain recursive splitter: {}".format(docs))
    return docs

def csdc_markdown_header_splitter(doc: Document) -> List[Document]:
    markdown_splitter = MarkdownHeaderTextSplitter()
    md_header_splits = markdown_splitter.split_text(doc)
    logger.info("csdc markdown header splitter: {}".format(md_header_splits)) 
    return md_header_splits

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

def openai_embedding(docs: List[Document]) -> List[List[float]]:
    embeddings = OpenAIEmbeddings()
    docs = documents_to_strings(docs)
    embeddings.embed_documents(docs)
    logger.info("openai embeddings: {}".format(embeddings))
    return embeddings

@retry(stop=stop_after_attempt(3))
def _aos_injection(document: Document) -> List[str]:
    """
    Returns:
        List of ids from adding the texts into the vectorstore.
    """
    embeddings = create_sagemaker_embeddings_from_js_model(embeddingModelEndpoint, region)
    docsearch = OpenSearchVectorSearch(
        index_name=default_aos_index_name,
        embedding_function=embeddings,
        opensearch_url="https://{}".format(aosEndpoint),
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    logger.info("Adding documents %s to OpenSearch with index %s", document, default_aos_index_name)
    res = docsearch.add_documents(documents=[document])
    logger.info("Retry statistics: %s and response: %s", _aos_injection.retry.statistics, res)
    return res

# this method require such aos was public accessible
def csdc_embedding_public(docs: List[Document]):
    for doc in docs:
        res = _aos_injection(doc)
        logger.info("aos injection result: {}".format(res))
    # TODO query the index with aos wrapper

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
    logger.info("retriever docs: {}".format(docs))
    db = FAISS.from_texts(texts, OpenAIEmbeddings())
    docs_with_score = db.similarity_search_with_score(query, 3)
    logger.info("docs_with_score: {}".format(docs_with_score))
    return docs_with_score

def csdc_retriver(texts: List[str], query: str):
    query_embedding = SagemakerEndpointVectorOrCross(
        prompt=query,
        endpoint_name=embeddingModelEndpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    # TODO, replace with aos wrapper
    # knn_respose = aos_client.search(
    #     index_name=default_aos_index_name, query_type="knn", query_term=query_embedding
    # )
    # return knn_respose

def langchain_evalutor(query: str, docs_with_score: List[Tuple[str, float]]):
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
    pass

import requests

def send_request(method: str, body=None):
    """
    Send a request to the specified URL with the given method and data.

    Args:
    url (str): The URL to which the request is sent.
    method (str): HTTP method ('GET', 'POST', 'PUT', etc.).
    data (dict, optional): The request body for methods like POST or PUT.

    Returns:
    Response object
    """
    if method.upper() == 'POST':
        response = requests.post(apiEndpoint, json=body)
    elif method.upper() == 'GET':
        response = requests.get(apiEndpoint, params=body)
    elif method.upper() == 'PUT':
        response = requests.put(apiEndpoint, json=body)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response

def csdc_embedding(index: str, doc: Document):
    """
    Embeds the given documents using the CSDC embedding model.

    Args:
        index (str): The name of the index to which the documents will be added.
        document (Document): The document to embed.

    Returns:
        list: A list of embeddings, one for each document.
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
    logger.info("payload: {}, apiEndpoint: {}, headers: {}, type: {}".format(payload, apiEndpoint, headers, type(payload)))
    try: 
        response = requests.request("POST", apiEndpoint + 'aos', headers=headers, data=payload)
        logger.info("response: {}".format(response))
    except Exception as e:
        logger.error("error: {}".format(e))
        raise e

# Preparing loader, splitter, and embeddings retriever list, iterate them to create comparasion matrix
loader_list = [unstructured_loader, nougat_loader, llamaIndex_loader]
splitter_list = [recursive_splitter, csdc_markdown_header_splitter]
embeddings_list = [openai_embedding]
retriever_list = [faiss_retriver, csdc_retriver]
evalutor_list = [langchain_evalutor]

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

    def execute_workflow(self, input_document, query):
        """
        Executes the workflow with all combinations of components and returns the results.

        Args:
            input_document (str): The input document to process.
            query (str): The query for retrieval and evaluation.

        Returns:
            list: A list of results from executing each workflow combination.

        Embedding evaluation: embedding into AOS using solution and langchain with different index , then using same question to query the retrieved references, calculate the similarities score between query and retrieved score, compare the score for both methods.

        E2E LLM evaluation: construct dataset with ground truth and using exiting langchain or llama index library to evaluate the faithfulness, relevance and accuracy metrics, OpenAI or Claude will be used as judger to determine the final score.
        """
        results_matrix = []
        for loader, splitter, embedder, retriever, evaluator in product(
            self.components['loaders'],
            self.components['splitters'],
            self.components['embedders'],
            self.components['retrievers'],
            self.components['evaluators']
        ):
            docs = loader(input_document)
            docs = splitter(docs)
            vectors = embedder.embed_documents(docs)
            retrieved_docs = retriever(docs, query)
            metrics = evaluator(retrieved_docs)
            results_matrix.append(metrics)

        return results_matrix

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

    # load
    loader_res = unstructured_loader("benchmark.md")

    # split
    for doc in loader_res:
        splitter_res = csdc_markdown_header_splitter(doc)

        for doc in splitter_res:
            # embedding
            embedding_res = csdc_embedding(default_aos_index_name, doc)

    # embedding
    # for doc in splitter_res:
    #     csdc_embedding(default_aos_index_name, doc)
    # embedding_res = csdc_embedding(default_aos_index_name, splitter_res[0])

    # # retriever
    # query = "什么是思维链？"
    # docs_with_score = faiss_retriver(docs, query = query)

    # # evaluator
    # result = langchain_evalutor(query, docs_with_score)

    # workflow = WorkflowExecutor()
    # workflow.update_component('loaders', unstructured_loader, 'add')
    # workflow.update_component('splitters', recursive_splitter, 'add')
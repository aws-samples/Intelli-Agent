import json
import logging
import time

from itertools import product
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader

from llm_bot_dep.loaders.nougat_pdf import NougatPDFLoader
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

sample_sample_markdown_document = """
# Learning to Retrieve In-Context Examples for Large Language Models
###### Abstract
aaaa
## 1 Introduction
1111
## 2 Related Work
2222
## 3 Preliminaries
3333
## 4 Methodology
4444
### Training Data Generation
5555
### Reward Modeling
6666
### Training LLM Retrievers with Knowledge Distillation
7777
### Evaluation of LLM Retrievers
8888
|-|-|
|:--:|:--:|
## 5 Experiments
### Evaluation Setup
9999
### Main Results
0000
### Training Pipeline of LLM-R
1010
### Generalization Ability of LLM-R
1212
### When does LLM-R Work and When Does it Not?
1313
### Using Different LLMs for Data Generation and Task Evaluation
1414
### Scaling the Number of In-Context Examples and Retriever Size
1515
## 7 Conclusion
1616
## Limitations
1717
## References
1818
"""

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

def csdc_markdown_header_splitter(docs: List[Document]) -> List[Document]:
    markdown_splitter = MarkdownHeaderTextSplitter()
    # construct a fake document data
    # data = [Document(page_content=sample_markdown_document, metadata=metadata_template)]
    md_header_splits = markdown_splitter.split_text(docs)
    for i, doc in enumerate(md_header_splits):
        logger.info("content of chunk %s: %s", i, doc)
    logger.info("csdc markdown splitter: {}".format(md_header_splits))
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

def langchain_evalutor(query: str, docs_with_score: List[Tuple[str, float]]):
    # evaluate the retriever
    from vectorview import Vectorview
    vv = Vectorview(key)
    vv.event(query, docs_with_score)

# Preparing loader, splitter, and embeddings retriever list, iterate them to create comparasion matrix
loader_list = [unstructured_loader]
splitter_list = [recursive_splitter, csdc_markdown_header_splitter]
embeddings_list = [openai_embedding]
retriever_list = [faiss_retriver]
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

    # load
    docs = unstructured_loader("paper-01.pdf")

    # split
    docs = recursive_splitter(docs)
    
    # embedding
    vector = openai_embedding(docs)

    # # retriever
    # query = "什么是思维链？"
    # docs_with_score = faiss_retriver(docs, query = query)

    # # evaluator
    # result = langchain_evalutor(query, docs_with_score)

    # workflow = WorkflowExecutor()
    # workflow.update_component('loaders', unstructured_loader, 'add')
    # workflow.update_component('splitters', recursive_splitter, 'add')
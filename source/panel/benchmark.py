import os
import logging
import time

from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

metadata_template = {
"content_type": "paragraph",
"heading_hierarchy": {},
"figure_list": [],
"chunk_id": "$$",
"file_path": "",
"keywords": [],
"summary": "",
}

markdown_document = """
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

def nougat_loader():
    # benchemark the nougat package
    # nougat ./2.pdf -o . --full-precision --markdown -m 0.1.0-base --recompute
    pass

def llamaIndex_loader(file_path: str):
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
        
def unstructured_loader(file_path: str):
    from langchain.document_loaders import UnstructuredFileLoader
    loader = UnstructuredFileLoader(file_path, mode="elements")
    docs = loader.load()
    logger.info("loader docs: {}".format(docs))
    return docs

def recursive_splitter(docs: List[Document]):
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap  = 30,
        length_function = len,
        add_start_index = True,
    )
    docs = text_splitter.split_documents(docs)
    logger.info("splitter docs: {}".format(docs))
    return docs

def csdc_markdown_header_splitter():
    from splitter_utils import MarkdownHeaderTextSplitter, Document
    markdown_splitter = MarkdownHeaderTextSplitter()
    # construct a fake document data
    data = [Document(page_content=markdown_document, metadata=metadata_template)]
    md_header_splits = markdown_splitter.split_text(data[0])
    for i, doc in enumerate(md_header_splits):
        logger.info("content of chunk %s: %s", i, doc)
    return md_header_splits

def openai_embedding():
    embeddings = OpenAIEmbeddings()
    return embeddings

def faiss_retriver(texts: List[str], query: str):
    retriever = FAISS.from_texts(texts, OpenAIEmbeddings()).as_retriever()
    docs = retriever.get_relevant_documents(query)
    logger.info("retriever docs: {}".format(docs))
    db = FAISS.from_texts(texts, OpenAIEmbeddings())
    docs_with_score = db.similarity_search_with_score(query, 3)
    logger.info("docs_with_score: {}".format(docs_with_score))
    return docs_with_score

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

# main entry point
if __name__ == "__main__":

    # Preparing loader, splitter, and embeddings retriever list, iterate them to create comparasion matrix
    loader_list = [unstructured_loader]
    splitter_list = [recursive_splitter, csdc_markdown_header_splitter]
    embeddings_list = []
    retriever_list = [faiss_retriver]

    # load
    docs = unstructured_loader("paper-01.pdf")

    # split
    docs = recursive_splitter(docs)
    
    # embedding & evaluate with dimension/time
    # In compatible with OpenAIEmbeddings
    texts = [doc.page_content for doc in docs]
    embedding_instance = openai_embedding()
    embeddings_list.append(embedding_instance)
    results = run_embeddings(embeddings_list, texts)

    # retriever
    query = "什么是思维链？"
    docs_with_score = faiss_retriver(texts, query = query)

    # evaluate retriever
        # evaluate the retriever
    # from vectorview import Vectorview
    # vv = Vectorview(key)
    # vv.event(query, docs_with_score)
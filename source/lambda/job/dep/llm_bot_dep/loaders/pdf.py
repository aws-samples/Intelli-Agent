import os
import re
import json
import logging

from langchain.docstore.document import Document
from langchain.document_loaders.pdf import BasePDFLoader
from langchain.document_loaders import PDFMinerPDFasHTMLLoader

from ..splitter_utils import extract_headings, MarkdownHeaderTextSplitter
from .html import CustomHtmlLoader

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

def detect_language(input):
    """
    This function detects the language of the input text. It checks if the input is a list, 
    and if so, it joins the list into a single string. Then it uses a regular expression to 
    search for Chinese characters in the input. If it finds any, it returns 'ch' for Chinese. 
    If it doesn't find any Chinese characters, it assumes the language is English and returns 'en'.
    """
    if isinstance(input, list):
        input = ' '.join(input)
    if re.search("[\u4e00-\u9FFF]", input):
        return 'ch'
    else:
        return 'en'


def process_pdf(s3, pdf: bytes, **kwargs):
    """
    Process a given PDF file and extracts structured information from it.

    This function reads a PDF file, converts it to HTML using PDFMiner, then extracts 
    and structures the information into a list of dictionaries containing headings and content.

    Parameters:
    s3 (boto3.client): The S3 client to use for downloading the PDF file.
    pdf (bytes): The PDF file to process.
    **kwargs: Arbitrary keyword arguments. The function expects 'bucket' and 'key' among the kwargs
              to specify the S3 bucket and key where the PDF file is located.

    Returns:
    list[Doucment]: A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata defined in metadata_template, and page_content string with the text content of that section.
    """
    logger.info("Processing PDF file...")
    bucket = kwargs['bucket']
    key = kwargs['key']
    # extract file name also in consideration of file name with blank space
    local_path = str(os.path.basename(key))
    # download to local for futher processing
    logger.info(local_path)
    s3.download_file(Bucket=bucket, Key=key, Filename=local_path)
    # TODO, will be deprecated and replaced by nougat class in loader_utils
    loader = PDFMinerPDFasHTMLLoader(local_path)
    # entire PDF is loaded as a single Document
    file_content = loader.load()[0].page_content
    
    loader = CustomHtmlLoader()
    doc = loader.load(file_content)
    splitter = MarkdownHeaderTextSplitter()
    doc_list = splitter.split_text(doc)

    for doc in doc_list:
        doc.metadata = metadata_template
        doc.metadata['file_path'] = f"s3://{bucket}/{key}"


    return doc_list

import os
import boto3
import sys
import re
import logging
import json
import itertools
import uuid
from datetime import datetime

from typing import Generator, Any, Dict, Iterable, List, Optional, Tuple
from bs4 import BeautifulSoup
import nltk

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PDFMinerPDFasHTMLLoader, CSVLoader
from langchain.docstore.document import Document
from langchain.vectorstores import OpenSearchVectorSearch
from opensearchpy import RequestsHttpConnection

from awsglue.utils import getResolvedOptions
from llm_bot_dep import sm_utils
from llm_bot_dep.loader_utils import NougatPDFLoader
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['NOUGAT_CHECKPOINT'] = '/tmp/nougat_checkpoint'
os.environ['NLTK_DATA'] = '/tmp/nltk_data'

# Parse arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'S3_PREFIX', 'AOS_ENDPOINT', 'EMBEDDING_MODEL_ENDPOINT', 'REGION', 'OFFLINE'])
s3_bucket = args['S3_BUCKET']
s3_prefix = args['S3_PREFIX']
aosEndpoint = args['AOS_ENDPOINT']
embeddingModelEndpoint = args['EMBEDDING_MODEL_ENDPOINT']
region = args['REGION']
offline = args['OFFLINE']

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

def fontsize_mapping(heading_fonts_arr):
    heading_fonts_set = list(set(heading_fonts_arr))
    heading_fonts_set.sort(reverse=True)
    idxs = range(len(heading_fonts_set))
    font_idx_mapping = dict(zip(heading_fonts_set,idxs))
    return font_idx_mapping

def link_header(semantic_snippets):
    """
    Processes a list of semantic snippets to organize and structure the header information based on font size,
    and then outputs the structured data as a JSON string.

    Parameters:
    semantic_snippets (list): A list of objects where each object has a 'metadata' attribute containing 'heading_font' and 'heading' fields.

    Returns:
    str: A JSON string representing the structured header and content information of each snippet.
    """
    heading_fonts_arr = [ item.metadata['heading_font'] for item in semantic_snippets ]
    heading_arr = [ item.metadata['heading'] for item in semantic_snippets ]        
    fontsize_dict = fontsize_mapping(heading_fonts_arr)

    snippet_arr = []
    for idx, snippet in enumerate(semantic_snippets):
        font_size = heading_fonts_arr[idx]
        heading_stack = []
        heading_info = {"font_size":heading_fonts_arr[idx], "heading":heading_arr[idx], "fontsize_idx" : fontsize_dict[font_size]}
        heading_stack.append(heading_info)
        for id in range(0,idx)[::-1]:
            if font_size < heading_fonts_arr[id]:
                font_size = heading_fonts_arr[id]
                heading_info = {"font_size":font_size, "heading":heading_arr[id], "fontsize_idx" : fontsize_dict[font_size]}
                heading_stack.append(heading_info)
            
        snippet_info = {
            "heading" : heading_stack,
            "content" : snippet.page_content
        }
        snippet_arr.append(snippet_info)
        
    json_arr = json.dumps(snippet_arr, ensure_ascii=False)
    return json_arr

def parse_pdf_to_json(file_content):
    """
    Credit to https://python.langchain.com/docs/modules/data_connection/document_loaders/pdf, parses the content of a PDF file converted to HTML format, organizing text segments semantically based on their font size.

    Parameters:
    file_content (str): The HTML content of the converted PDF file.

    Returns:
    list: A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading and content font sizes, and a page_content string with the text content of that section.

    Notes:
    - Assumes that headings have a larger font size than their respective content.
    - It first iterates through all the text segments, grouping consecutive segments with the same font size together.
    - Then, iterates through these grouped segments, identifying new headings based on a change in font size, and grouping the content under these headings.
    - The function is designed to work with a specific HTML structure and may not work as expected with differently structured HTML.
    """
    soup = BeautifulSoup(file_content,'html.parser')
    content = soup.find_all('div')

    cur_fs = None
    cur_text = ''
    snippets = []   # first collect all snippets that have the same font size
    for c in content:
        sp = c.find('span')
        if not sp:
            continue
        st = sp.get('style')
        if not st:
            continue
        fs = re.findall('font-size:(\d+)px',st)
        if not fs:
            continue
        fs = int(fs[0])
        if not cur_fs:
            cur_fs = fs
        if fs == cur_fs:
            cur_text += c.text
        else:
            snippets.append((cur_text,cur_fs))
            cur_fs = fs
            cur_text = c.text
    snippets.append((cur_text,cur_fs))

    cur_idx = -1
    semantic_snippets = []
    # Assumption: headings have higher font size than their respective content
    for s in snippets:
        # if current snippet's font size > previous section's heading => it is a new heading
        if not semantic_snippets or s[1] > semantic_snippets[cur_idx].metadata['heading_font']:
            metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
            #metadata.update(data.metadata)
            semantic_snippets.append(Document(page_content='',metadata=metadata))
            cur_idx += 1
            continue
        
        # if current snippet's font size <= previous section's content => content belongs to the same section (one can also create
        # a tree like structure for sub sections if needed but that may require some more thinking and may be data specific)
        if not semantic_snippets[cur_idx].metadata['content_font'] or s[1] <= semantic_snippets[cur_idx].metadata['content_font']:
            semantic_snippets[cur_idx].page_content += s[0]
            semantic_snippets[cur_idx].metadata['content_font'] = max(s[1], semantic_snippets[cur_idx].metadata['content_font'])
            continue
        
        # if current snippet's font size > previous section's content but less tha previous section's heading than also make a new 
        # section (e.g. title of a pdf will have the highest font size but we don't want it to subsume all sections)
        metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
        #metadata.update(data.metadata)
        semantic_snippets.append(Document(page_content='',metadata=metadata))
        cur_idx += 1

    res = link_header(semantic_snippets)
    return res

def pre_process_text(text: str):
    # Remove special characters, punctuation, line breaks and multiple spaces with a single space,
    str_doc = re.sub(r'[^\w\s]', '', text)
    str_doc = re.sub(r'\s+', ' ', str_doc)
    str_doc = re.sub(r'\n', ' ', str_doc)
    return str_doc.strip()

def post_process_pdf(pdf: str):
    """
    Transforms a given string of a specific format into a desired formatted string.

    The function extracts the 'page_content' value from the input string and
    constructs a new string in a JSON-like format with specific hardcoded values
    and the extracted 'page_content' value.

    Parameters:
    -----------
    original_string : str
        The input string to be transformed. Sample: 
        str: A string formatted in the desired JSON-like structure. Sample:
        [
            {
                "heading": [
                    {
                        "font_size": 10,
                        "heading": "5\n1\n0\n2\ny\na\nM\n8\n1\n",
                        "fontsize_idx": 2
                    }
                ],
                "content": "this is the content\n"
            }
            ...
        ]
    Returns:
    --------
        str: A string to conform to AOS embedding wrapper. Sample:
        List[Document]
        [Document(page_content='this is the content', metadata={'source': '/tmp/tmpghff3i39/xx/dth.txt', 'timestamp': 1697513348.1026106, 'embeddings_model': 'embedding-endpoint'})]
    """
    logger.info("Post-processing PDF file %s", pdf)
    # Parse the input string to a Python data structure
    input_data = json.loads(pdf)
    # Create an empty list to hold the Document objects
    documents: List[Document] = []

    # Iterate through the parsed data, creating Document objects for each item
    for item in input_data:
        page_content = item['content']
        # Assuming some default metadata; adjust as necessary
        metadata = {'source': 'unknown', 'fontsize': item['heading'][0]['font_size'], 'heading': item['heading'][0]['heading'], 'fontsize_idx': item['heading'][0]['fontsize_idx']}
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    logger.info("Post-processing PDF with result %s", documents)
    return documents


def process_text(text: str):
    logger.info("Processing text file...")
    text = pre_process_text(text)


def process_csv(csv_content: str, **kwargs):
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    bucket_name = kwargs['bucket']
    key = kwargs['key']
    row_count = kwargs['csv_row_count']
    local_path = f'/tmp/csv-{timestamp_str}-{random_uuid}.csv'

    s3.download_file(bucket_name, key, local_path)
    logger.info(f"CSV file downloaded to {local_path}")
    loader = loader_utils.CustomCSVLoader(file_path=local_path, row_count=row_count)
    data = loader.load()

    return data


def process_html(htmlstr: str):
    logger.info("Processing HTML file...")
    # filter out DOCTYPE
    htmlstr = ' '.join(htmlstr.split())
    re_doctype = re.compile(r'<!DOCTYPE .*?>', re.S)
    s = re_doctype.sub('', htmlstr)
    
    # filter out CDATA
    re_cdata = re.compile('//<!\[CDATA\[[^>]*//\]\]>', re.I)
    s = re_cdata.sub('', s)
    
    # filter out Script
    re_script = re.compile('<\s*script[^>]*>[^<]*<\s*/\s*script\s*>', re.I)
    s = re_script.sub('', s)
    
    # filter out style
    re_style = re.compile('<\s*style[^>]*>[^<]*<\s*/\s*style\s*>', re.I)
    s = re_style.sub('', s)
    
    # transfor br to \n
    re_br = re.compile('<br\s*?/?>')
    s = re_br.sub('', s)
    
    # filter out HTML tags
    re_h = re.compile('<\?[\w+[^>]*>')
    s = re_h.sub('', s)
    
    # filter out HTML comments
    re_comment = re.compile('<!--[^>]*-->')
    s = re_comment.sub('', s)
    
    # remove extra blank lines
    blank_line = re.compile('\n+')
    s = blank_line.sub('', s)
    
    # remove hyperlinks
    http_link = re.compile(r'(http://.+html)')
    s = http_link.sub('', s)
    
    return s

def process_pdf(pdf: bytes, **kwargs):
    """
    Process a given PDF file and extracts structured information from it.

    This function reads a PDF file, converts it to HTML using PDFMiner, then extracts 
    and structures the information into a list of dictionaries containing headings and content.

    Parameters:
    pdf (bytes): The PDF file to process.
    **kwargs: Arbitrary keyword arguments. The function expects 'bucket' and 'key' among the kwargs
              to specify the S3 bucket and key where the PDF file is located.

    Returns:
    list: A list of dictionaries, each containing 'heading' and 'content' keys. 
          The 'heading' key maps to a list of dictionaries with keys 'font_size', 'heading', 
          and 'fontsize_idx'. The 'content' key maps to a string containing the content under 
          that heading.
    [
        {
            "heading": [
                {
                    "font_size": 10,
                    "heading": "5\n1\n0\n2\ny\na\nM\n8\n1\n",
                    "fontsize_idx": 2
                }
            ],
            "content": "xxxx\n"
        },
        ...
    }
    Usage: process_pdf(pdf_bytes, bucket='my-bucket', key='documents/doc.pdf')

    Note: 
    - The extracted headings and content are dependent on the structure and formatting of the PDF.
    - The S3 bucket and key are used to download the file to a local path for processing.
    """
    logger.info("Processing PDF file...")
    bucket = kwargs['bucket']
    key = kwargs['key']
    # extract file name also in consideration of file name with blank space
    local_path = str(os.path.basename(key))
    # download to local for futher processing
    s3.download_file(Bucket=bucket, Key=key, Filename=local_path)
    # TODO, will be deprecated and replaced by nougat class in loader_utils
    # loader = PDFMinerPDFasHTMLLoader(local_path)
    # entire PDF is loaded as a single Document
    # file_content = loader.load()[0].page_content
    # res = parse_pdf_to_json(file_content)

    loader = NougatPDFLoader(local_path)
    data = loader.load()
    # logger.info("raw data: %s", data)
    markdown_splitter = MarkdownHeaderTextSplitter()
    md_header_splits = markdown_splitter.split_text(data[0])
    for i, doc in enumerate(md_header_splits):
        logger.info("PDF file processed successfully, with content of chunk %s: %s", i, doc)
    return md_header_splits

def process_image(image: bytes):
    logger.info("Processing image file...")
    # TODO: Implement image processing with ASK API

def cb_process_object(file_type: str, file_content, **kwargs):
    res = None
    if file_type == 'text':
        process_text(file_content, **kwargs)
    elif file_type == 'csv':
        res = process_csv(file_content, **kwargs)
        # CSV page document has been splited into chunk, no more spliting is needed
        aos_injection(res, embeddingModelEndpoint, aosEndpoint, 'chatbot-index', gen_chunk=False)
    elif file_type == 'html':
        process_html(file_content, **kwargs)
    elif file_type == 'pdf':
        # res = post_process_pdf(process_pdf(file_content, **kwargs))
        res = process_pdf(file_content, **kwargs)
        aos_injection(res, embeddingModelEndpoint, aosEndpoint, 'chatbot-index')
    elif file_type == 'image':
        process_image(file_content, **kwargs)
    return res

def iterate_s3_files(bucket: str, prefix: str) -> Generator:    
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            # skip the prefix with slash, which is the folder name
            if obj['Key'].endswith('/'):
                continue
            key = obj['Key']
            file_type = key.split('.')[-1]  # Extract file extension

            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()
            # assemble bucket and key as args for the callback function
            kwargs = {'bucket': bucket, 'key': key}

            if file_type in ['txt']:
                yield 'text', file_content.decode('utf-8'), kwargs
            elif file_type in ['csv']:
                # Update row count here, the default row count is 1
                kwargs['csv_row_count'] = 1
                yield 'csv', file_content.decode('utf-8'), kwargs
            elif file_type in ['html']:
                yield 'html', file_content.decode('utf-8'), kwargs
            elif file_type in ['pdf']:
                yield 'pdf', file_content, kwargs
            elif file_type in ['jpg', 'png']:
                yield 'image', file_content, kwargs
            else:
                logger.info(f"Unknown file type: {file_type}")

def batch_generator(generator, batch_size: int):
    iterator = iter(generator)
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break
        yield batch

def aos_injection(content: List[Document], embeddingModelEndpoint: str, aosEndpoint: str, index_name: str, chunk_size: int = 500, gen_chunk: bool = True) -> List[Document]:

    """
    This function includes the following steps:
    1. split the document into chunks with chunk size to fit the embedding model, note the document is already splited by title/subtitle to form sementic chunks approximately;
    2. call the embedding model to get the embeddings for each chunk;
    3. call the AOS to index the chunk with the embeddings;
    Parameters:
    content (list): A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading hierarchy etc.
    embeddingModelEndpoint (str): The endpoint of the embedding model.
    aosEndpoint (str): The endpoint of the AOS.
    index_name (str): The name of the index to be created in the AOS.
    chunk_size (int): The size of each chunk to be indexed in the AOS.

    Returns:

    Note:
    """
    # This function includes the following steps:
    # 1. split the document into chunks with chunk size to fit the embedding model, note the document is already splited by title/subtitle to form sementic chunks approximately;
    # 2. call the embedding model to get the embeddings for each chunk;
    # 3. call the AOS to index the chunk with the embeddings;
    embeddings = sm_utils.create_sagemaker_embeddings_from_js_model(embeddingModelEndpoint, region)

    def chunk_generator(content: List[Document], chunk_size: int = 500, chunk_overlap: int = 30) -> Generator[Document, None, None]:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for document in content:
            splits = text_splitter.split_documents([document])
            # list of Document objects
            for split in splits:
                yield split

    if gen_chunk:
        generator = chunk_generator(content, chunk_size=chunk_size)
    else:
        generator = content

    batches = batch_generator(generator, batch_size=10)
    # note: typeof(batch)->list[Document], sizeof(batches)=batch_size
    for batch in batches:
        if len(batch) == 0:
            continue
        logger.info("Adding documents %s to OpenSearch with index %s", batch, index_name)
        # TODO, parse the metadata to embed with different index
        docsearch = OpenSearchVectorSearch(
            index_name=index_name,
            embedding_function=embeddings,
            opensearch_url="https://{}".format(aosEndpoint),
            http_auth = awsauth,
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection
        )
        docsearch.add_documents(documents=batch)

# main function to be called by Glue job script
def main():
    logger.info("Starting Glue job with passing arguments: %s", args)
    # check if offline mode
    if offline == 'true':
        logger.info("Running in offline mode with consideration for large file size...")
        for file_type, file_content, kwargs in iterate_s3_files(s3_bucket, s3_prefix):
            try:
                res = cb_process_object(file_type, file_content, **kwargs)
                if res:
                    logger.info("Result: %s", res)
            except Exception as e:
                logger.error("Error processing object %s: %s", kwargs['bucket'] + '/' + kwargs['key'], e)
    else:
        logger.info("Running in online mode, assume file number is small...")

if __name__ == '__main__':
    logger.info("boto3 version: %s", boto3.__version__)
 
    # Set the NLTK data path to the /tmp directory for AWS Glue jobs
    nltk.data.path.append("/tmp")
    # List of NLTK packages to download
    nltk_packages = ['words']
    # Download the required NLTK packages to /tmp
    for package in nltk_packages:
        # download the package to /tmp/nltk_data
        nltk.download(package, download_dir='/tmp/nltk_data')
    main()
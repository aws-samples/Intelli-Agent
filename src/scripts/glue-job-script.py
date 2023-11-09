import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
import sys
import logging
import itertools
import time

from typing import Generator, Any, Dict, Iterable, List, Optional, Tuple
import nltk

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.vectorstores import OpenSearchVectorSearch
from opensearchpy import RequestsHttpConnection

from awsglue.utils import getResolvedOptions
from llm_bot_dep import sm_utils
from llm_bot_dep.loaders.auto import cb_process_object
from llm_bot_dep.enhance_utils import EnhanceWithBedrock

from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['NOUGAT_CHECKPOINT'] = '/tmp/nougat_checkpoint'
os.environ['NLTK_DATA'] = '/tmp/nltk_data'

# Parse arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'S3_PREFIX', 'AOS_ENDPOINT', 'EMBEDDING_MODEL_ENDPOINT', 'REGION', 'OFFLINE', 'QA_ENHANCEMENT', 'BATCH_INDICE', 'ProcessedObjectsTable'])
s3_bucket = args['S3_BUCKET']
s3_prefix = args['S3_PREFIX']
aosEndpoint = args['AOS_ENDPOINT']
embeddingModelEndpoint = args['EMBEDDING_MODEL_ENDPOINT']
region = args['REGION']
offline = args['OFFLINE']
qa_enhancement = args['QA_ENHANCEMENT']
# TODO, pass the bucket and prefix need to handle in current job directly
batchIndice = args['BATCH_INDICE']
processedObjectsTable = args['ProcessedObjectsTable']

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(processedObjectsTable)

ENHANCE_CHUNK_SIZE = 500
# Make it 3600s for debugging purpose
OBJECT_EXPIRY_TIME = 3600

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

# such glue job is running as map job, the batchIndice is the index per file to handle in current job
def iterate_s3_files(bucket: str, prefix: str) -> Generator:    
    paginator = s3.get_paginator('list_objects_v2')
    currentIndice = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            # skip the prefix with slash, which is the folder name
            if key.endswith('/'):
                continue

            # skip the file if the index is not in the batchIndice
            if currentIndice != int(batchIndice):
                logger.info("currentIndice: {}, batchIndice: {}, skip file: {}".format(currentIndice, batchIndice, key))
                currentIndice += 1
                continue

            # Truncate to seconds with round()
            current_time = int(round(time.time()))
            # Check for redundancy and expiry
            response = table.query(
                KeyConditionExpression = Key('ObjectKey').eq(key),
                ScanIndexForward=False,  # Sort by ProcessTimestamp in descending order
                Limit=1  # We only need the latest record
            )

            # If the object is found and has not expired, skip processing
            if response['Items'] and response['Items'][0]['ExpiryTimestamp'] > current_time:
                logger.info(f"Object {key} has not expired yet and will be skipped.")
                continue

            # Record the processing of the S3 object with an updated expiry timestamp, and each job only update single object in table. TODO, current assume the object will be handled successfully
            expiry_timestamp = current_time + OBJECT_EXPIRY_TIME
            try:
                table.put_item(
                    Item={
                        'ObjectKey': key,
                        'ProcessTimestamp': current_time,
                        'Bucket': bucket,
                        'Prefix': '/'.join(key.split('/')[:-1]),
                        'ExpiryTimestamp': expiry_timestamp
                    }
                )
            except Exception as e:
                logger.error(f"Error recording processed of S3 object {key}: {e}")

            file_type = key.split('.')[-1]  # Extract file extension
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()
            # assemble bucket and key as args for the callback function
            kwargs = {'bucket': bucket, 'key': key}

            if file_type in ['txt']:
                yield 'txt', file_content.decode('utf-8'), kwargs
                break
            elif file_type in ['csv']:
                # Update row count here, the default row count is 1
                kwargs['csv_row_count'] = 1
                yield 'csv', file_content.decode('utf-8'), kwargs
                break
            elif file_type in ['html']:
                yield 'html', file_content.decode('utf-8'), kwargs
                break
            elif file_type in ['pdf']:
                yield 'pdf', file_content, kwargs
                break
            elif file_type in ['jpg', 'png']:
                yield 'image', file_content, kwargs
                break
            elif file_type in ['docx', 'doc']:
                yield 'doc', file_content.decode('utf-8'), kwargs
                break
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
    gen_chunk (bool): Whether generate chunks or not.

    Returns:

    Note:
    """
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
        # the batch are still list of Document objects, we need to iterate the list to inject the embeddings, the chunk size (500) should already be small enough to fit the embedding model
        for document in batch:
            @retry(stop=stop_after_attempt(3))
            def _aos_injection(document: Document) -> Document:
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
                logger.info("Adding documents %s to OpenSearch with index %s", document, index_name)
                docsearch.add_documents(documents=[document])
                logger.info("Retry statistics: %s", _aos_injection.retry.statistics)
            # logger.info("Adding documents %s to OpenSearch with index %s", document, index_name)
            _aos_injection(document)

# Main function to be called by Glue job script
def main():
    logger.info("Starting Glue job with passing arguments: %s", args)
    # Check if offline mode
    if offline == 'true':
        logger.info("Running in offline mode with consideration for large file size...")
        for file_type, file_content, kwargs in iterate_s3_files(s3_bucket, s3_prefix):
            try:
                res = cb_process_object(s3, file_type, file_content, **kwargs)
                # TODO, parse the metadata to embed with different index
                if res:
                    logger.info("Result: %s", res)
                if file_type == 'csv':
                    # CSV page document has been splited into chunk, no more spliting is needed
                    aos_injection(res, embeddingModelEndpoint, aosEndpoint, 'chatbot-index', gen_chunk=False)
                elif file_type == 'html':
                    aos_injection(res, embeddingModelEndpoint, aosEndpoint, 'chatbot-index')
                elif file_type in ['pdf', 'txt']:
                    aos_injection(res, embeddingModelEndpoint, aosEndpoint, 'chatbot-index')
                    if qa_enhancement == 'true':
                        # iterate the document to get the QA pairs
                        for document in res:
                            # prompt is not used in this case
                            prompt = ""
                            solution_title = "GCR Solution LLM Bot"
                            # Make sure the document is Document object
                            logger.info("Enhancing document type: {} and content: {}".format(type(document), document))
                            ewb = EnhanceWithBedrock(prompt, solution_title, document)
                            # This is should be optional for the user to choose the chunk size
                            document_list = ewb.SplitDocumentByTokenNum(document, ENHANCE_CHUNK_SIZE)
                            # test the function
                            for document in document_list:
                                enhanced_prompt = ewb.EnhanceWithClaude(prompt, solution_title, document)
                                logger.info("Enhanced prompt: {}".format(enhanced_prompt))

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
        # Download the package to /tmp/nltk_data
        nltk.download(package, download_dir='/tmp/nltk_data')
    main()

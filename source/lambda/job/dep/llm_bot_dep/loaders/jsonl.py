from typing import Iterable, List
import json
import logging
from langchain.docstore.document import Document

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

def process_jsonl(s3, jsonl: bytes, **kwargs)->List[Document]:
    """
    Process the jsonl file include query and answer pairs or other k-v alike data, in format of:
    {"question": "<question 1>", "answer": "<answer 1>"}
    {"question": "<question 2>", "answer": "<answer 2>"}
    ...

    We will extract the question and assemble the content in page_content of Document, extract the answer and assemble as extra field in metadata (jsonlAnswer) of Document.

    :param jsonl: jsonl file content
    :param kwargs: other arguments

    :return: list of Document, e.g.
    [
        Document(page_content="<question 1>", metadata={"jsonlAnswer": "<answer 1>, other metadata in metadata_template"}),
        Document(page_content="<question 2>", metadata={"jsonlAnswer": "<answer 2>, other metadata in metadata_template"}),
        ...
    ]
    """
    logger.info("Processing jsonl file...")
    bucket = kwargs['bucket']
    key = kwargs['key']

    try:
        # load the jsonl file from bytes directly and split into lines
        jsonl_list = jsonl.decode('utf-8').split('\n')

        doc_list = []
        for jsonl_line in jsonl_list:
            try:
                # load the jsonl line as a json object
                json_obj = json.loads(jsonl_line)
                # extract the question
                page_content = json_obj['question']
                # assemble the metadata
                metadata = metadata_template
                metadata['jsonlAnswer'] = json_obj['answer']
                metadata['file_path'] = f"s3://{bucket}/{key}"
                # assemble the Document
                doc = Document(page_content=page_content, metadata=metadata)
                doc_list.append(doc)
            except json.JSONDecodeError as e:
                logger.error(f"jsonl_line: {jsonl_line} is not a valid json object, error: {e}")
                continue
            except KeyError as e:
                logger.error(f"jsonl_line: {jsonl_line} does not contain key: {e}")
    except UnicodeDecodeError as e:
        logger.error(f"jsonl file is not utf-8 encoded, error: {e}")
        raise e

    logger.info(f"processed jsonl_list: {doc_list} and if it is iterable: {isinstance(doc_list, Iterable)}")
    return doc_list

# main entry point
if __name__ == "__main__":
    import boto3
    import os

    # set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # set up boto3
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket='delete-me-jack-us-east-1', Key='llm-jsonl/jsonl.jsonl')
    file_content = response["Body"].read()
    
    process_jsonl(s3, file_content, bucket='delete-me-jack-us-east-1', key='llm-jsonl/jsonl.jsonl')
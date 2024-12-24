import json
import uuid
import logging
from typing import Iterable, List
from datetime import datetime
import pandas as pd
from langchain.docstore.document import Document


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_xlsx(s3, **kwargs) -> List[Document]:
    """
    Process the Excel file
    We will extract the question and assemble the content in page_content of Document, extract the answer and assemble as extra field in metadata (jsonlAnswer) of Document.

    :param kwargs: other arguments
    :return: list of Document, e.g.
    [
        Document(page_content="<question 1>", metadata={"jsonlAnswer": "<answer 1>, other metadata in metadata_template"}),
        Document(page_content="<question 2>", metadata={"jsonlAnswer": "<answer 2>, other metadata in metadata_template"}),
        ...
    ]
    """
    logger.info("Processing xlsx file...")
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    row_count = kwargs["xlsx_row_count"]
    local_path = f"/tmp/excel-{timestamp_str}-{random_uuid}.xlsx"

    s3.download_file(bucket_name, key, local_path)

    try:
        # load the excel file
        df = pd.read_excel(local_path)
        columns = df.columns
        doc_list = []
        if "question" in columns.tolist() and "answer" in columns.tolist():
            for index, json_obj in df.iterrows():
                try:
                    # instantiate the metadata template for each document
                    metadata_template = {
                        "content_type": "paragraph",
                        "heading_hierarchy": {},
                        "figure_list": [],
                        "chunk_id": "$$",
                        "file_path": "",
                        "keywords": [],
                        "summary": "",
                    }
                    # load the jsonl line as a json object
                    # extract the question
                    page_content = json_obj["question"]
                    # assemble the metadata
                    metadata = metadata_template
                    metadata["jsonlAnswer"] = json_obj["answer"]
                    metadata["file_path"] = f"s3://{bucket_name}/{key}"
                    logger.info(
                        "question: {}, answer: {}".format(
                            json_obj["question"], json_obj["answer"]
                        )
                    )
                    # assemble the Document
                    doc = Document(page_content=page_content,
                                   metadata=metadata)
                    doc_list.append(doc)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"line: {str(json_obj)} is not a valid json object, error: {e}"
                    )
                    continue
                except KeyError as e:
                    logger.error(
                        f"line: {str(json_obj)} does not contain key: {e}")
        else:
            from .csv import CustomCSVLoader            
            local_temp_path = local_path.replace('.xlsx', '.csv')
            df.to_csv(local_temp_path, index=None)
            loader = CustomCSVLoader(
                file_path=local_temp_path, aws_path=f"s3://{bucket_name}/{key}", row_count=row_count
            )
            doc_list = loader.load()
    except UnicodeDecodeError as e:
        logger.error(f"Excel file is not utf-8 encoded, error: {e}")
        raise e

    logger.info(
        f"processed excel file: {doc_list} and if it is iterable: {isinstance(doc_list, Iterable)}"
    )
    return doc_list

import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Union

import pandas as pd
from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.loaders.csv import CustomCSVLoader
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import download_file_from_s3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomXlsxLoader(BaseLoader):
    """Load xlsx from a file path.

    Args:
        file_path: Path to the file to load.
        s3_uri: S3 URI of the file to load.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        s3_uri: str,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.s3_uri = s3_uri
        self.metadata_template = {
            "content_type": "paragraph",
            "heading_hierarchy": {},
            "figure_list": [],
            "chunk_id": "$$",
            "file_path": "",
            "keywords": [],
            "summary": "",
        }

    def load(self, rows_per_document: int = 1) -> List[Document]:
        """Load from file path.
        
        Returns:
            List of Document objects.
        """
        doc_list = []
        try:
            # load the excel file
            df = pd.read_excel(self.file_path)
            columns = df.columns
            if "question" in columns.tolist() and "answer" in columns.tolist():
                for index, json_obj in df.iterrows():
                    try:
                        # load the jsonl line as a json object
                        # extract the question
                        page_content = json_obj["question"]
                        # assemble the metadata
                        metadata = self.metadata_template
                        metadata["jsonlAnswer"] = json_obj["answer"]
                        metadata["file_path"] = self.s3_uri
                        logger.info(
                            "question: {}, answer: {}".format(
                                json_obj["question"], json_obj["answer"]
                            )
                        )
                        # assemble the Document
                        doc = Document(page_content=page_content, metadata=metadata)
                        doc_list.append(doc)
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"line: {str(json_obj)} is not a valid json object, error: {e}"
                        )
                        continue
                    except KeyError as e:
                        logger.error(
                            f"line: {str(json_obj)} does not contain key: {e}"
                        )
            else:
                local_temp_path = self.file_path.replace(".xlsx", ".csv")
                df.to_csv(local_temp_path, index=None)
                loader = CustomCSVLoader(
                    file_path=local_temp_path,
                    s3_uri=self.s3_uri,
                )
                doc_list = loader.load(rows_per_document=rows_per_document)
        except UnicodeDecodeError as e:
            logger.error(f"Excel file is not utf-8 encoded, error: {e}")
            raise e

        logger.info(
            f"processed excel file: {doc_list} and if it is iterable: {isinstance(doc_list, Iterable)}"
        )
        return doc_list

def process_xlsx(processing_params: ProcessingParameters) -> List[Document]:
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
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    suffix = Path(key).suffix
    
    # Create a temporary file with .csv suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)

    # Use the loader with the local file path
    loader = CustomXlsxLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc_list = loader.load(rows_per_document=processing_params.xlsx_rows_per_document)

    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)
    return doc_list

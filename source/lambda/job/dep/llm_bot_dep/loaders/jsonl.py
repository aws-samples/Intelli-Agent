import json
import logging
import tempfile
from pathlib import Path
from typing import Iterable, List

from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import download_file_from_s3, load_content_from_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomJsonlLoader(BaseLoader):
    """Load markdown file.

    Args:
        file_path: Path to the file to load.
        s3_uri: S3 URI of the file to load.
    """

    def __init__(
        self,
        file_path: str,
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

    def load(self):
        """Load from file path."""
        content = load_content_from_file(self.file_path)
        doc_list = []

        try:
            # load the jsonl file from bytes directly and split into lines
            jsonl_list = content.split("\n")

            for jsonl_line in jsonl_list:
                try:
                    # load the jsonl line as a json object
                    json_obj = json.loads(jsonl_line)

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
                        f"jsonl_line: {jsonl_line} is not a valid json object, error: {e}"
                    )
                    continue
                except KeyError as e:
                    logger.error(
                        f"jsonl_line: {jsonl_line} does not contain key: {e}"
                    )
        except UnicodeDecodeError as e:
            logger.error(f"jsonl file is not utf-8 encoded, error: {e}")
            raise e

        logger.info(
            f"processed jsonl_list: {doc_list} and if it is iterable: {isinstance(doc_list, Iterable)}"
        )
        return doc_list


def process_jsonl(processing_params: ProcessingParameters) -> List[Document]:
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
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    suffix = Path(key).suffix
    
    # Create a temporary file with .txt suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)
    
    # Use the loader with the local file path
    loader = CustomJsonlLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc_list = loader.load()
    
    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)

    return doc_list

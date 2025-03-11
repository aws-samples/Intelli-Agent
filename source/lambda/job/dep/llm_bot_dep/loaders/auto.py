from typing import Any, Callable, Dict, List, Optional

from langchain.docstore.document import Document
from llm_bot_dep.loaders.csv import process_csv
from llm_bot_dep.loaders.docx import process_doc
from llm_bot_dep.loaders.html import process_html
from llm_bot_dep.loaders.image import process_image
from llm_bot_dep.loaders.json import process_json
from llm_bot_dep.loaders.jsonl import process_jsonl
from llm_bot_dep.loaders.markdown import process_md
from llm_bot_dep.loaders.pdf import process_pdf
from llm_bot_dep.loaders.text import process_text
from llm_bot_dep.loaders.xlsx import process_xlsx
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

# Registry of file processors mapped by file extension
FILE_PROCESSORS: Dict[str, Callable] = {
    "csv": process_csv,
    "doc": process_doc,
    "docx": process_doc,
    "html": process_html,
    "json": process_json,
    "jsonl": process_jsonl,
    "md": process_md,
    "pdf": process_pdf,
    "txt": process_text,
    "xlsx": process_xlsx,
    "png": process_image,
    "jpg": process_image,
    "jpeg": process_image,
    "webp": process_image,
}

FILE_TYPES_WITHOUT_SPLITTER = ["csv", "xlsx", "jsonl"]


def process_object(processing_params: ProcessingParameters) -> List[Document]:
    """
    Process a document based on its file type using the appropriate processor.
    
    Args:
        processing_params: Parameters containing file type and other processing information
        
    Returns:
        List of Document objects containing the processed content
        
    Raises:
        ValueError: If the file type is not supported
    """
    file_type = processing_params.file_type.lower()
    
    # Get the appropriate processor function from the registry
    processor = FILE_PROCESSORS.get(file_type)
    
    if not processor:
        supported_types = ", ".join(FILE_PROCESSORS.keys())
        raise ValueError(
            f"Unsupported file type: '{file_type}'. Supported types are: {supported_types}"
        )
    
    # Process the document using the selected processor
    doc_list = processor(processing_params)
    if file_type in FILE_TYPES_WITHOUT_SPLITTER:
        return doc_list
    else:
        splitter = MarkdownHeaderTextSplitter(processing_params.result_bucket_name)
        split_docs = []
        for doc in doc_list:
            split_docs.extend(splitter.split_text(doc))
        return split_docs

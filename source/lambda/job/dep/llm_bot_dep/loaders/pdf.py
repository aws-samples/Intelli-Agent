import os
import re
import json
import logging
from bs4 import BeautifulSoup
import subprocess
from pathlib import Path
from typing import List, Dict, List, Optional, Iterator, Sequence

from langchain.docstore.document import Document
from langchain.document_loaders import PDFMinerPDFasHTMLLoader

from langchain.document_loaders.pdf import BasePDFLoader
from ..splitter_utils import extract_headings, MarkdownHeaderTextSplitter
# from langchain.text_splitter import MarkdownHeaderTextSplitter

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

class NougatPDFLoader(BasePDFLoader):
    """A PDF loader class for converting PDF files to MMD.

    This class leverages the `nougat` library to perform the conversion from PDF to HTML.
    It inherits from `BasePDFLoader` and extends its functionality to utilize the `nougat` library.
    TODO, the load_and_split method need to be implemented and default is RecursiveCharacterTextSplitter
    Attributes:
        file_path (str): The path to the PDF file to be loaded.
        headers (Optional[Dict]): Optional headers to be used when loading the PDF.

    Raises:
        ImportError: If the `nougat` library is not installed.
        RuntimeError: If the `nougat` command fails to execute successfully.
    """

    def __init__(self, file_path: str, *, headers: Optional[Dict] = None):
        """Initialize with a file path."""
        try:
            import nougat
        except ImportError:
            raise ImportError(
                "Please install nougat to use NougatPDFLoader. "
                "You can install it with `pip install nougat`."
            )

        super().__init__(file_path, headers=headers)

    def nougat(self, file_path: Path) -> str:
        """Executes the `nougat` command to convert the specified PDF file to Markdown format.

        Args:
            file_path (Path): The path to the PDF file to be converted.

        Returns:
            str: The Markdown content resulting from the `nougat` conversion.
        """
        # nougat ./paperSnapshot.pdf --full-precision --markdown -m 0.1.0-base -o tmp --recompute
        cli_command = ["nougat", str(file_path), "full-precision", "--markdown", "-m", "0.1.0-base", "-o", "tmp", "--recompute"]

        try:
            result = subprocess.run(
                cli_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            result.check_returncode()
            return result.stdout

        except subprocess.CalledProcessError as e:
            logger.info(
                f"Nougat command failed with return code {e.returncode}: {e.stderr}"
            )
            raise RuntimeError("Nougat command failed.") from e

    def load(self) -> List[Document]:
        """Loads and processes the specified PDF file, converting it to a list of Document objects.

        Returns:
            List[Document]: A list containing a single Document object with the processed content.
        """
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load and process the specified PDF file, yielding Document objects.

        This method reads the PDF file, processes it using the `nougat` command,
        reads the resulting Markdown content, and yields a Document object with the content.
        """
        # try:
        file_path = self.file_path
        # Call the method to run the Nougat OCR command
        self.nougat(file_path)

        # Rest of your code for reading and processing the output
        file_path = Path(file_path)
        output_path = Path("tmp") / f"{file_path.stem}.mmd"
        with output_path.open("r") as f:
            content = f.read()
        # consider math expressions are enclosed in \( and \) in Markdown
        content = (
            content.replace(r"\(", "$")
            .replace(r"\)", "$")
            .replace(r"\[", "$$")
            .replace(r"\]", "$$")
        )
        logger.info("content: %s", content)
        # extract headings hierarchically
        headings = extract_headings(content)

        # assemble metadata from template
        metadata = metadata_template
        metadata["content_type"] = "paragraph"
        metadata["heading_hierarchy"] = headings
        metadata["chunk_id"] = "$$"
        metadata["file_path"] = str(file_path)
        # TODO, use PyMuPDF to detect image and figure list, but no link to the image for the extracted text
        # metadata["figure_list"] = []

        yield Document(page_content=content, metadata=metadata)

        # except Exception as e:
        #     logger.info(f"An error occurred while processing the PDF: {str(e)}")


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
    # loader = PDFMinerPDFasHTMLLoader(local_path)
    # entire PDF is loaded as a single Document
    # file_content = loader.load()[0].page_content
    # res = parse_pdf_to_json(file_content)

    loader = NougatPDFLoader(local_path)
    data = loader.load()
    logger.info("raw data: %s", data)
    # Update file_path metadata to full s3 path in list of Document objects
    data[0].metadata['file_path'] = f"s3://{bucket}/{key}"
    markdown_splitter = MarkdownHeaderTextSplitter()
    md_header_splits = markdown_splitter.split_text(data[0])
    for i, doc in enumerate(md_header_splits):
        logger.info("PDF file processed successfully, with content of chunk %s: %s", i, doc)
    return md_header_splits

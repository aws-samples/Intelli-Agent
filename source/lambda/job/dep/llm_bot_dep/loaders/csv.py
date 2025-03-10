import csv
import tempfile
import uuid
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from langchain.docstore.document import Document
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders.helpers import detect_file_encodings
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import download_file_from_s3


class CustomCSVLoader(CSVLoader):
    """Load a `CSV` file into a list of Documents.

    Each document represents one row of the CSV file. The rows are converted into markdown format based on row_count.

    Output Example:
        when row_count = 1,
        page_document_1 contains:
        |index|name|
        |-|-|
        |1|Demo1|
        page_document_2 contains:
        |index|name|
        |-|-|
        |2|Demo2|

        when row_count = 3,
        page_document_1 contains:
        |index|name|
        |-|-|
        |1|Demo1|
        |2|Demo2|
        |3|Demo3|
        page_document_2 contains:
        |index|name|
        |-|-|
        |4|Demo4|
        |5|Demo5|
        |6|Demo6|
    """

    def __init__(
        self,
        file_path: str,
        s3_uri: str,
        source_column: Optional[str] = None,
        metadata_columns: Sequence[str] = (),
        csv_args: Optional[Dict] = None,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """
        Args:
            file_path: The path to the CSV file.
            source_column: The name of the column in the CSV file to use as the source. Optional. Defaults to None.
            metadata_columns: A sequence of column names to use as metadata. Optional.
            csv_args: A dictionary of arguments to pass to the csv.DictReader. Optional. Defaults to None.
            encoding: The encoding of the CSV file. Optional. Defaults to None.
            autodetect_encoding: Whether to try to autodetect the file encoding.
        """
        self.s3_uri = s3_uri
        super().__init__(
            file_path,
            source_column,
            metadata_columns,
            csv_args,
            encoding,
            autodetect_encoding,
        )

    def __read_file(self, csvfile: TextIOWrapper, rows_per_document: int = 1) -> List[Document]:
        doc_list = []

        csv_reader = csv.DictReader(csvfile, **self.csv_args)
        counter = 0
        for i, row in enumerate(csv_reader):
            counter += 1

            if counter % rows_per_document == 1:
                # First row with header and separator
                header = "|"
                md_separator = "|"
                row_content = "|"
                for k, v in row.items():
                    header += k + "|"
                    md_separator += "-|"
                    row_content += v + "|"
                row_content += "\n"
            elif counter % rows_per_document == 0:
                if rows_per_document == 1:
                    header = "|"
                    md_separator = "|"
                    row_content = "|"
                    for k, v in row.items():
                        header += k + "|"
                        md_separator += "-|"
                        row_content += v + "|"
                else:
                    for k, v in row.items():
                        row_content += v + "|"
                content = header + "\n" + md_separator + "\n" + row_content

                metadata = {
                    "row": i,
                    "file_path": self.s3_uri,
                    "file_type": "csv"
                }
                for col in self.metadata_columns:
                    try:
                        metadata[col] = row[col]
                    except KeyError:
                        raise ValueError(
                            f"Metadata column '{col}' not found in CSV file."
                        )
                doc = Document(page_content=content, metadata=metadata)
                doc_list.append(doc)
                counter = 0
            else:
                for k, v in row.items():
                    row_content += v + "|"
                row_content += "\n"

        return doc_list

    def load(self, rows_per_document: int = 1) -> List[Document]:
        """Load data into document objects."""

        doc_list = []
        try:
            with open(
                self.file_path, newline="", encoding=self.encoding
            ) as csvfile:
                doc_list = self.__read_file(csvfile, rows_per_document)
        except UnicodeDecodeError as e:
            if self.autodetect_encoding:
                detected_encodings = detect_file_encodings(self.file_path)
                for encoding in detected_encodings:
                    try:
                        with open(
                            self.file_path,
                            newline="",
                            encoding=encoding.encoding,
                        ) as csvfile:
                            doc_list = self.__read_file(csvfile)
                            break
                    except UnicodeDecodeError:
                        continue
            else:
                raise RuntimeError(f"Error loading {self.file_path}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading {self.file_path}") from e

        return doc_list


def process_csv(processing_params: ProcessingParameters):
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    suffix = Path(key).suffix
    
    # Create a temporary file with .csv suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)

    # Use the loader with the local file path
    loader = CustomCSVLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc_list = loader.load(rows_per_document=processing_params.csv_rows_per_document)

    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)
    return doc_list

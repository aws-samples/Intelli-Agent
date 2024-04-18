import csv
import uuid
from datetime import datetime
from io import TextIOWrapper
from typing import Dict, Iterator, List, Optional, Sequence

from langchain.docstore.document import Document
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.document_loaders.helpers import detect_file_encodings


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
        aws_path: str,
        source_column: Optional[str] = None,
        metadata_columns: Sequence[str] = (),
        csv_args: Optional[Dict] = None,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
        row_count: int = 1,
    ):
        """

        Args:
            file_path: The path to the CSV file.
            source_column: The name of the column in the CSV file to use as the source. Optional. Defaults to None.
            metadata_columns: A sequence of column names to use as metadata. Optional.
            csv_args: A dictionary of arguments to pass to the csv.DictReader. Optional. Defaults to None.
            encoding: The encoding of the CSV file. Optional. Defaults to None.
            autodetect_encoding: Whether to try to autodetect the file encoding.
            row_count: How many row in a page document.
        """
        self.row_number = row_count
        self.aws_path = aws_path
        super().__init__(
            file_path,
            source_column,
            metadata_columns,
            csv_args,
            encoding,
            autodetect_encoding,
        )

    def __read_file(self, csvfile: TextIOWrapper) -> List[Document]:
        docs = []

        csv_reader = csv.DictReader(csvfile, **self.csv_args)
        counter = 0
        for i, row in enumerate(csv_reader):
            try:
                source = (
                    row[self.source_column]
                    if self.source_column is not None
                    else self.file_path
                )
            except KeyError:
                raise ValueError(
                    f"Source column '{self.source_column}' not found in CSV file."
                )
            counter += 1

            if counter % self.row_number == 1:
                # First row with header and separator
                header = "|"
                md_separator = "|"
                row_content = "|"
                for k, v in row.items():
                    header += k + "|"
                    md_separator += "-|"
                    row_content += v + "|"
                row_content += "\n"
            elif counter % self.row_number == 0:
                if 1 == self.row_number:
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
                print(f"markdown content: {content}")

                metadata = {"source": source, "row": i, "file_path": self.aws_path}
                for col in self.metadata_columns:
                    try:
                        metadata[col] = row[col]
                    except KeyError:
                        raise ValueError(
                            f"Metadata column '{col}' not found in CSV file."
                        )
                doc = Document(page_content=content, metadata=metadata)
                docs.append(doc)
                counter = 0
            else:
                for k, v in row.items():
                    row_content += v + "|"
                row_content += "\n"

        return docs

    def load(self) -> List[Document]:
        """Load data into document objects."""

        docs = []
        try:
            with open(self.file_path, newline="", encoding=self.encoding) as csvfile:
                docs = self.__read_file(csvfile)
        except UnicodeDecodeError as e:
            if self.autodetect_encoding:
                detected_encodings = detect_file_encodings(self.file_path)
                for encoding in detected_encodings:
                    try:
                        with open(
                            self.file_path, newline="", encoding=encoding.encoding
                        ) as csvfile:
                            docs = self.__read_file(csvfile)
                            break
                    except UnicodeDecodeError:
                        continue
            else:
                raise RuntimeError(f"Error loading {self.file_path}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading {self.file_path}") from e

        return docs


def process_csv(s3, csv_content: str, **kwargs):
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    row_count = kwargs["csv_row_count"]
    local_path = f"/tmp/csv-{timestamp_str}-{random_uuid}.csv"

    s3.download_file(bucket_name, key, local_path)
    loader = CustomCSVLoader(
        file_path=local_path, aws_path=f"s3://{bucket_name}/{key}", row_count=row_count
    )
    data = loader.load()

    return data

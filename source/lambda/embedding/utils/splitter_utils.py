import re
import logging
import uuid
from typing import Any, Dict, Iterator, List, Optional, Union
import boto3
from langchain.docstore.document import Document
from langchain.text_splitter import (
    Language,
    RecursiveCharacterTextSplitter,
    TextSplitter,
)
from storage_utils import save_content_to_s3
from constant import SplittingType


s3 = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _make_spacy_pipeline_for_splitting(pipeline: str) -> Any:  # avoid importing spacy
    try:
        import spacy
    except ImportError:
        raise ImportError(
            "Spacy is not installed, please install it with `pip install spacy`."
        )
    if pipeline == "sentencizer":
        from spacy.lang.en import English

        sentencizer = English()
        sentencizer.add_pipe("sentencizer")
    else:
        sentencizer = spacy.load(pipeline, exclude=["ner", "tagger"])
    return sentencizer


class NLTKTextSplitter(TextSplitter):
    """Splitting text using NLTK package."""

    def __init__(
        self, separator: str = "\n\n", language: str = "english", **kwargs: Any
    ) -> None:
        """Initialize the NLTK splitter."""
        super().__init__(**kwargs)
        try:
            from nltk.tokenize import sent_tokenize

            self._tokenizer = sent_tokenize
        except ImportError:
            raise ImportError(
                "NLTK is not installed, please install it with `pip install nltk`."
            )
        self._separator = separator
        self._language = language

    def split_text(self, text: str) -> List[str]:
        """Split incoming text and return chunks."""
        # First we naively split the large input into a bunch of smaller ones.
        splits = self._tokenizer(text, language=self._language)
        return self._merge_splits(splits, self._separator)


class SpacyTextSplitter(TextSplitter):
    """Splitting text using Spacy package.


    Per default, Spacy's `en_core_web_sm` model is used. For a faster, but
    potentially less accurate splitting, you can use `pipeline='sentencizer'`.
    """

    def __init__(
        self, separator: str = "\n\n", pipeline: str = "en_core_web_sm", **kwargs: Any
    ) -> None:
        """Initialize the spacy text splitter."""
        super().__init__(**kwargs)
        self._tokenizer = _make_spacy_pipeline_for_splitting(pipeline)
        self._separator = separator

    def split_text(self, text: str) -> List[str]:
        """Split incoming text and return chunks."""
        splits = (s.text for s in self._tokenizer(text).sents)
        return self._merge_splits(splits, self._separator)


def find_parent(headers: dict, level: int):
    """Find the parent node of current node
    Find the last node whose level is less than current node

    Args:
        headers (dict): headers dict
        level (int): level of the header, eg. # is level1, ## is level2

    Returns:
        _type_: parent node id or None
    """
    for id, header in reversed(list(headers.items())):
        if header["level"] < level:
            return id

    return None


def find_previous_with_same_level(headers: dict, level: int):
    """Find the previous node with same level

    Args:
        headers (dict): headers dict
        level (int): level of the header, eg. # is level1, ## is level2

    Returns:
        _type_: previous node id or None
    """
    for id, header in reversed(list(headers.items())):
        if header["level"] == level:
            return id

    return None


def find_next_with_same_level(headers: dict, header_id: str):
    level = headers[header_id]["level"]
    header_found = False

    for id, header in headers.items():
        if header_id == id:
            header_found = True

        # Find the next node with the same level
        if header_found and header["level"] == level and header_id != id:
            return id

    return None


def find_child(headers: dict, header_id: str):
    children = []
    level = headers[header_id]["level"]

    for id, header in headers.items():
        if (
            header["level"] == level + 1
            and id not in children
            and header["parent"] == header_id
        ):
            children.append(id)

    return children


def extract_headings(md_content: str):
    """Extract heading hierarchy from Markdown content.
    Args:
        md_content (str): Markdown content.
    Returns:
        Json object contains the heading hierarchy
    """
    header_index = 0
    headers = {}
    lines = md_content.split("\n")
    id_index_dict = {}
    for line in lines:
        match = re.match(r"(#+)(.*)", line)
        if match:
            header_index += 1
            print(match.group)
            level = len(match.group(1))
            title = match.group(2).strip()
            id_prefix = str(uuid.uuid4())[:8]
            _id = f"${header_index}-{id_prefix}"
            parent = find_parent(headers, level)
            previous = find_previous_with_same_level(headers, level)
            headers[_id] = {
                "title": title,
                "level": level,
                "parent": parent,
                "previous": previous,
            }
            # Use list in case multiple heading have the same title
            if title not in id_index_dict:
                id_index_dict[title] = [_id]
            else:
                id_index_dict[title].append(_id)

    for header_obj in headers:
        headers[header_obj]["child"] = find_child(headers, header_obj)
        headers[header_obj]["next"] = find_next_with_same_level(headers, header_obj)

    return headers, id_index_dict


# Rewrite this class to use the new TextSplitter for mmd type
class MarkdownHeaderTextSplitter:
    # Place holder for now without parameters
    def __init__(self, res_bucket: str = None):
        self.res_bucket = res_bucket

    def _is_markdown_header(self, line):
        header_pattern = r"^#+\s+"
        if re.match(header_pattern, line):
            return True
        else:
            return False

    def _is_markdown_table_row(self, line):
        return re.fullmatch(r"\|.*\|.*\|", line) is not None

    def _set_chunk_id(
        self,
        id_index_dict: dict,
        current_heading: str,
        metadata: dict,
        same_heading_dict: dict,
    ):
        """Set chunk id when there are multiple headings are the same.
        Eg.
        # Heading 1
        ## Same heading
        # Heading 2
        ## Same heading

        Args:
            id_index_dict (dict): Id and index mapping
            current_heading (str): Current heading
            metadata (dict): Metadata
            same_heading_dict (dict): Same heading mapping
        """
        if 1 == len(id_index_dict[current_heading]):
            metadata["chunk_id"] = id_index_dict[current_heading][0]
        elif len(id_index_dict[current_heading]) > 1:
            # If multiple headings are the same in the document,
            # use index in same_heading_dict to get the chunk_id
            if current_heading not in same_heading_dict:
                same_heading_dict[current_heading] = 0
                metadata["chunk_id"] = id_index_dict[current_heading][0]
            else:
                # Move one step to get the next chunk_id
                same_heading_dict[current_heading] += 1
                if len(id_index_dict[current_heading]) > same_heading_dict[current_heading]:
                    metadata["chunk_id"] = id_index_dict[current_heading][
                        same_heading_dict[current_heading]
                    ]
                else:
                    id_prefix = str(uuid.uuid4())[:8]
                    metadata["chunk_id"] = f"$0-{id_prefix}"

    def split_text(self, text: Document) -> List[Document]:
        if self.res_bucket is not None:
            # save_content_to_s3(s3, text, self.res_bucket, SplittingType.BEFORE.value)
            pass
        else:
            logger.warning(
                "No resource bucket is defined, skip saving content into S3 bucket"
            )

        lines = text.page_content.strip().split("\n")
        chunks = []
        current_chunk_content = []
        same_heading_dict = {}
        table_content = []
        inside_table = False
        heading_hierarchy, id_index_dict = extract_headings(text.page_content.strip())
        if len(lines) > 0:
            current_heading = lines[0]

        for line in lines:
            # Replace escaped characters for table markers
            line = line.strip()
            line = line.replace(r"\begin{table}", "\\begin{table}").replace(
                r"\end{table}", "\\end{table}"
            )
            if line in ["\\begin{table}", "\\end{table}"]:
                continue

            if self._is_markdown_header(line):  # Assuming these denote headings
                # Save the current chunk if it exists
                if current_chunk_content:
                    metadata = text.metadata.copy()
                    metadata["content_type"] = "paragragh"
                    metadata["current_heading"] = current_heading
                    current_heading = current_heading.replace("#", "").strip()
                    try:
                        self._set_chunk_id(
                            id_index_dict, current_heading, metadata, same_heading_dict
                        )
                    except KeyError:
                        logger.info(
                            f"No standard heading found, check your document with {current_chunk_content}"
                        )
                        id_prefix = str(uuid.uuid4())[:8]
                        metadata["chunk_id"] = f"$0-{id_prefix}"
                    if metadata["chunk_id"] in heading_hierarchy:
                        metadata["heading_hierarchy"] = heading_hierarchy[
                            metadata["chunk_id"]
                        ]
                    chunks.append(
                        Document(
                            page_content="\n".join(current_chunk_content),
                            metadata=metadata,
                        )
                    )
                    current_chunk_content = []  # Reset for the next chunk
                current_heading = line

            if self._is_markdown_table_row(line):
                inside_table = True
            elif inside_table:
                # The first line under a table
                inside_table = False
                # Save table content as a separate document
                if table_content:
                    metadata = text.metadata.copy()
                    metadata["content_type"] = "table"
                    metadata["current_heading"] = current_heading
                    current_heading = current_heading.replace("#", "").strip()
                    try:
                        self._set_chunk_id(
                            id_index_dict, current_heading, metadata, same_heading_dict
                        )
                    except KeyError:
                        logger.info(f"No standard heading found")
                        id_prefix = str(uuid.uuid4())[:8]
                        metadata["chunk_id"] = f"$0-{id_prefix}"
                    if metadata["chunk_id"] in heading_hierarchy:
                        metadata["heading_hierarchy"] = heading_hierarchy[
                            metadata["chunk_id"]
                        ]
                    chunks.append(
                        Document(
                            page_content="\n".join(table_content), metadata=metadata
                        )
                    )
                    table_content = []  # Reset for the next table

            if inside_table:
                table_content.append(line)
            else:
                current_chunk_content.append(line)

        # Save the last chunk if it exists
        if current_chunk_content:
            metadata = text.metadata.copy()
            metadata["content_type"] = "paragragh"
            metadata["current_heading"] = current_heading
            current_heading = current_heading.replace("#", "").strip()
            try:
                self._set_chunk_id(
                    id_index_dict, current_heading, metadata, same_heading_dict
                )
            except KeyError:
                logger.info(f"No standard heading found")
                id_prefix = str(uuid.uuid4())[:8]
                metadata["chunk_id"] = f"$0-{id_prefix}"
            if metadata["chunk_id"] in heading_hierarchy:
                metadata["heading_hierarchy"] = heading_hierarchy[metadata["chunk_id"]]
            chunks.append(
                Document(
                    page_content="\n".join(current_chunk_content), metadata=metadata
                )
            )

        return chunks

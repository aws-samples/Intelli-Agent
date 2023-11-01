import re
from typing import Any, Dict, List, Optional, Iterator, Union
from langchain.docstore.document import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    Language,
    TextSplitter,
)

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

class NestedDict(dict):
    def __missing__(self, key):
        self[key] = NestedDict()
        return self[key]

def extract_headings(md_content):
    """Extract headings hierarchically from Markdown content.
    Consider alternate syntax that "any number of == characters for heading level 1 or -- characters for heading level 2."
    See https://www.markdownguide.org/basic-syntax/
    Args:
        md_content (str): Markdown content.
    Returns:
        NestedDict: A nested dictionary containing the headings. Sample output:
        {
            'Title 1': {
                'Subtitle 1.1': {},
                'Subtitle 1.2': {}
            },
            'Title 2': {
                'Subtitle 2.1': {}
            }
        }
    """
    headings = NestedDict()
    current_heads = [headings]
    lines = md_content.strip().split('\n')

    for i, line in enumerate(lines):
        match = re.match(r'(#+) (.+)', line)
        if not match and i > 0:  # If the line is not a heading, check if the previous line is a heading using alternate syntax
            if re.match(r'=+', lines[i - 1]):
                level = 1
                title = lines[i - 2]
            elif re.match(r'-+', lines[i - 1]):
                level = 2
                title = lines[i - 2]
            else:
                continue
        elif match:
            level = len(match.group(1))
            title = match.group(2)
        else:
            continue

        current_heads = current_heads[:level]
        current_heads[-1][title]
        current_heads.append(current_heads[-1][title])

    return headings

# rewrite this class to use the new TextSplitter for mmd type
class MarkdownHeaderTextSplitter:
    # Place holder for now without parameters
    def __init__(self) -> None:
        pass

    def split_text(self, text: Document) -> List[Document]:
        lines = text.page_content.strip().split('\n')
        chunks = []
        current_chunk_content = []
        chunk_id = 1  # Initializing chunk_id

        for line in lines:
            if line.startswith(('## ', ' ### ')):  # Assuming these denote headings
                # Save the current chunk if it exists
                if current_chunk_content:
                    metadata = text.metadata.copy()
                    metadata['heading_hierarchy'] = extract_headings('\n'.join(current_chunk_content))
                    metadata['chunk_id'] = f"${chunk_id}"
                    chunk_id += 1
                    chunks.append(Document(page_content='\n'.join(current_chunk_content), metadata=metadata))
                    current_chunk_content = []  # Reset for the next chunk

            current_chunk_content.append(line)

        # Save the last chunk if it exists
        if current_chunk_content:
            metadata = text.metadata.copy()
            metadata['heading_hierarchy'] = extract_headings('\n'.join(current_chunk_content))
            metadata['chunk_id'] = f"${chunk_id}"
            chunks.append(Document(page_content='\n'.join(current_chunk_content), metadata=metadata))

        return chunks


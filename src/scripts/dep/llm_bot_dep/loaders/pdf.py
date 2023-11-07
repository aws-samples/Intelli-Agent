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

class NestedDict(dict):
    def __missing__(self, key):
        self[key] = NestedDict()
        return self[key]


# rewrite this class to use the new TextSplitter for mmd type
class MarkdownHeaderTextSplitter:
    # Place holder for now without parameters
    def __init__(self) -> None:
        pass

    def split_text(self, text: Document) -> List[Document]:
        lines = text.page_content.strip().split('\n')
        chunks = []
        current_chunk_content = []
        table_content = []
        inside_table = False
        chunk_id = 1  # Initializing chunk_id

        for line in lines:
            # Replace escaped characters for table markers
            line = line.replace(r"\begin{table}", "\\begin{table}").replace(r"\end{table}", "\\end{table}")
            if line.strip() == "\\begin{table}":
                inside_table = True
                continue  # Skip this line
            elif line.strip() == "\\end{table}":
                inside_table = False
                # Save table content as a separate document
                if table_content:
                    metadata = text.metadata.copy()
                    metadata['content_type'] = 'table'
                    metadata['chunk_id'] = f"${chunk_id}"
                    chunks.append(Document(page_content='\n'.join(table_content), metadata=metadata))
                    table_content = []  # Reset for the next table
                continue  # Skip this line

            if inside_table:
                table_content.append(line)
            elif line.startswith(('## ', ' ### ')):  # Assuming these denote headings
                # Save the current chunk if it exists
                if current_chunk_content:
                    metadata = text.metadata.copy()
                    metadata['heading_hierarchy'] = extract_headings('\n'.join(current_chunk_content))
                    metadata['chunk_id'] = f"${chunk_id}"
                    chunk_id += 1  # Increment chunk_id for the next chunk
                    chunks.append(Document(page_content='\n'.join(current_chunk_content), metadata=metadata))
                    current_chunk_content = []  # Reset for the next chunk

            if not inside_table:
                current_chunk_content.append(line)

        # Save the last chunk if it exists
        if current_chunk_content:
            metadata = text.metadata.copy()
            metadata['heading_hierarchy'] = extract_headings('\n'.join(current_chunk_content))
            metadata['chunk_id'] = f"${chunk_id}"
            chunks.append(Document(page_content='\n'.join(current_chunk_content), metadata=metadata))

        return chunks


# TODO, this function is duplicated in splitter_utils.py, need to merge to one place
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


def fontsize_mapping(heading_fonts_arr):
    heading_fonts_set = list(set(heading_fonts_arr))
    heading_fonts_set.sort(reverse=True)
    idxs = range(len(heading_fonts_set))
    font_idx_mapping = dict(zip(heading_fonts_set,idxs))
    return font_idx_mapping

def link_header(semantic_snippets):
    """
    Processes a list of semantic snippets to organize and structure the header information based on font size,
    and then outputs the structured data as a JSON string.

    Parameters:
    semantic_snippets (list): A list of objects where each object has a 'metadata' attribute containing 'heading_font' and 'heading' fields.

    Returns:
    str: A JSON string representing the structured header and content information of each snippet.
    """
    heading_fonts_arr = [ item.metadata['heading_font'] for item in semantic_snippets ]
    heading_arr = [ item.metadata['heading'] for item in semantic_snippets ]        
    fontsize_dict = fontsize_mapping(heading_fonts_arr)

    snippet_arr = []
    for idx, snippet in enumerate(semantic_snippets):
        font_size = heading_fonts_arr[idx]
        heading_stack = []
        heading_info = {"font_size":heading_fonts_arr[idx], "heading":heading_arr[idx], "fontsize_idx" : fontsize_dict[font_size]}
        heading_stack.append(heading_info)
        for id in range(0,idx)[::-1]:
            if font_size < heading_fonts_arr[id]:
                font_size = heading_fonts_arr[id]
                heading_info = {"font_size":font_size, "heading":heading_arr[id], "fontsize_idx" : fontsize_dict[font_size]}
                heading_stack.append(heading_info)
            
        snippet_info = {
            "heading" : heading_stack,
            "content" : snippet.page_content
        }
        snippet_arr.append(snippet_info)
        
    json_arr = json.dumps(snippet_arr, ensure_ascii=False)
    return json_arr

def parse_pdf_to_json(file_content):
    """
    Credit to https://python.langchain.com/docs/modules/data_connection/document_loaders/pdf, parses the content of a PDF file converted to HTML format, organizing text segments semantically based on their font size.

    Parameters:
    file_content (str): The HTML content of the converted PDF file.

    Returns:
    list: A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading and content font sizes, and a page_content string with the text content of that section.

    Notes:
    - Assumes that headings have a larger font size than their respective content.
    - It first iterates through all the text segments, grouping consecutive segments with the same font size together.
    - Then, iterates through these grouped segments, identifying new headings based on a change in font size, and grouping the content under these headings.
    - The function is designed to work with a specific HTML structure and may not work as expected with differently structured HTML.
    """
    soup = BeautifulSoup(file_content,'html.parser')
    content = soup.find_all('div')

    cur_fs = None
    cur_text = ''
    snippets = []   # first collect all snippets that have the same font size
    for c in content:
        sp = c.find('span')
        if not sp:
            continue
        st = sp.get('style')
        if not st:
            continue
        fs = re.findall('font-size:(\d+)px',st)
        if not fs:
            continue
        fs = int(fs[0])
        if not cur_fs:
            cur_fs = fs
        if fs == cur_fs:
            cur_text += c.text
        else:
            snippets.append((cur_text,cur_fs))
            cur_fs = fs
            cur_text = c.text
    snippets.append((cur_text,cur_fs))

    cur_idx = -1
    semantic_snippets = []
    # Assumption: headings have higher font size than their respective content
    for s in snippets:
        # if current snippet's font size > previous section's heading => it is a new heading
        if not semantic_snippets or s[1] > semantic_snippets[cur_idx].metadata['heading_font']:
            metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
            #metadata.update(data.metadata)
            semantic_snippets.append(Document(page_content='',metadata=metadata))
            cur_idx += 1
            continue
        
        # if current snippet's font size <= previous section's content => content belongs to the same section (one can also create
        # a tree like structure for sub sections if needed but that may require some more thinking and may be data specific)
        if not semantic_snippets[cur_idx].metadata['content_font'] or s[1] <= semantic_snippets[cur_idx].metadata['content_font']:
            semantic_snippets[cur_idx].page_content += s[0]
            semantic_snippets[cur_idx].metadata['content_font'] = max(s[1], semantic_snippets[cur_idx].metadata['content_font'])
            continue
        
        # if current snippet's font size > previous section's content but less tha previous section's heading than also make a new 
        # section (e.g. title of a pdf will have the highest font size but we don't want it to subsume all sections)
        metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
        #metadata.update(data.metadata)
        semantic_snippets.append(Document(page_content='',metadata=metadata))
        cur_idx += 1

    res = link_header(semantic_snippets)
    return res


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

def post_process_pdf(s3, pdf: str):
    """
    Transforms a given string of a specific format into a desired formatted string.

    The function extracts the 'page_content' value from the input string and
    constructs a new string in a JSON-like format with specific hardcoded values
    and the extracted 'page_content' value.

    Parameters:
    -----------
    original_string : str
        The input string to be transformed. Sample: 
        str: A string formatted in the desired JSON-like structure. Sample:
        [
            {
                "heading": [
                    {
                        "font_size": 10,
                        "heading": "5\n1\n0\n2\ny\na\nM\n8\n1\n",
                        "fontsize_idx": 2
                    }
                ],
                "content": "this is the content\n"
            }
            ...
        ]
    Returns:
    --------
        str: A string to conform to AOS embedding wrapper. Sample:
        List[Document]
        [Document(page_content='this is the content', metadata={'source': '/tmp/tmpghff3i39/xx/dth.txt', 'timestamp': 1697513348.1026106, 'embeddings_model': 'embedding-endpoint'})]
    """
    logger.info("Post-processing PDF file %s", pdf)
    # Parse the input string to a Python data structure
    input_data = json.loads(pdf)
    # Create an empty list to hold the Document objects
    documents: List[Document] = []

    # Iterate through the parsed data, creating Document objects for each item
    for item in input_data:
        page_content = item['content']
        # Assuming some default metadata; adjust as necessary
        metadata = {'source': 'unknown', 'fontsize': item['heading'][0]['font_size'], 'heading': item['heading'][0]['heading'], 'fontsize_idx': item['heading'][0]['fontsize_idx']}
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    logger.info("Post-processing PDF with result %s", documents)
    return documents

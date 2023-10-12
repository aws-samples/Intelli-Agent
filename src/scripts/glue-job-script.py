import os
import boto3
import sys
import re
import logging
import json

from typing import Generator
from bs4 import BeautifulSoup
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
from langchain.docstore.document import Document

from awsglue.utils import getResolvedOptions

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# Parse arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'S3_PREFIX', 'AOS_ENDPOINT', 'EMBEDDING_MODEL_ENDPOINT'])
s3_bucket = args['S3_BUCKET']
s3_prefix = args['S3_PREFIX']

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

def pre_process_text(text: str):
    # Remove special characters, punctuation, line breaks and multiple spaces with a single space, 
    str_doc = re.sub(r'[^\w\s]', '', str_doc)    
    str_doc = re.sub(r'\s+', ' ', str_doc)
    str_doc = re.sub(r'\n', ' ', str_doc)
    return str_doc.strip()

def process_text(text: str):
    logger.info("Processing text file...")
    text = pre_process_text(text)

def process_html(htmlstr: str):
    logger.info("Processing HTML file...")
    # filter out DOCTYPE
    htmlstr = ' '.join(htmlstr.split())
    re_doctype = re.compile(r'<!DOCTYPE .*?>', re.S)
    s = re_doctype.sub('', htmlstr)
    
    # filter out CDATA
    re_cdata = re.compile('//<!\[CDATA\[[^>]*//\]\]>', re.I)
    s = re_cdata.sub('', s)
    
    # filter out Script
    re_script = re.compile('<\s*script[^>]*>[^<]*<\s*/\s*script\s*>', re.I)
    s = re_script.sub('', s)
    
    # filter out style
    re_style = re.compile('<\s*style[^>]*>[^<]*<\s*/\s*style\s*>', re.I)
    s = re_style.sub('', s)
    
    # transfor br to \n
    re_br = re.compile('<br\s*?/?>')
    s = re_br.sub('', s)
    
    # filter out HTML tags
    re_h = re.compile('<\?[\w+[^>]*>')
    s = re_h.sub('', s)
    
    # filter out HTML comments
    re_comment = re.compile('<!--[^>]*-->')
    s = re_comment.sub('', s)
    
    # remove extra blank lines
    blank_line = re.compile('\n+')
    s = blank_line.sub('', s)
    
    # remove hyperlinks
    http_link = re.compile(r'(http://.+html)')
    s = http_link.sub('', s)
    
    return s

def process_pdf(pdf: bytes, **kwargs):
    logger.info("Processing PDF file...")
    bucket = kwargs['bucket']
    key = kwargs['key']
    local_path = os.path.basename(key)
    # download to local for futher processing
    s3.download_file(Bucket=bucket, Key=bucket, Filename=local_path)
    loader = PDFMinerPDFasHTMLLoader(local_path)
    # entire PDF is loaded as a single Document
    file_content = loader.load()[0].page_content
    res = parse_pdf_to_json(file_content)
    logger.info("PDF file processed successfully, with result: %s", res)
    return res

def process_image(image: bytes):
    logger.info("Processing image file...")
    # TODO: Implement image processing with ASK API

def cb_process_object(file_type: str, file_content, **kwargs):
    if file_type == 'text':
        process_text(file_content, **kwargs)
    elif file_type == 'html':
        process_html(file_content, **kwargs)
    elif file_type == 'pdf':
        process_pdf(file_content, **kwargs)
    elif file_type == 'image':
        process_image(file_content, **kwargs)

def iterate_s3_files(bucket: str, prefix: str) -> Generator:    
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            file_type = key.split('.')[-1]  # Extract file extension

            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()
            # assemble bucket and key as args for the callback function
            kwargs = {'bucket': bucket, 'key': key}

            if file_type in ['txt', 'csv']:
                yield 'text', file_content.decode('utf-8'), kwargs
            elif file_type in ['html']:
                yield 'html', file_content.decode('utf-8'), kwargs
            elif file_type in ['pdf']:
                yield 'pdf', file_content, kwargs
            elif file_type in ['jpg', 'png']:
                yield 'image', file_content, kwargs
            else:
                print(f"Unknown file type: {file_type}")

# main function to be called by Glue job script
logger.info("Starting Glue job with passing arguments: %s", args)
for file_type, file_content, kwargs in iterate_s3_files(s3_bucket, s3_prefix):
    cb_process_object(file_type, file_content, **kwargs)

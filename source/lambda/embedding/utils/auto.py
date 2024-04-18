# from .docx import process_doc
# from .markdown import process_md
# from .text import process_text
# from .csvx import process_csv
# from .htmlx import process_html
# from .image import process_image
# from .json import process_json
# from .jsonl import process_jsonl
import logging

from .pdf import process_pdf

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def cb_process_object(s3, file_type: str, file_content, **kwargs):
    logger.info(f"Processing file type: {file_type}")
    res = None
    # leave pdf only before we move to other type for sync invocation since there are still timeout issue in api gw
    if file_type == "pdf":
        res = process_pdf(s3, file_content, **kwargs)
    # if file_type == "txt":
    #     res = process_text(file_content, **kwargs)
    # elif file_type == "csv":
    #     res = process_csv(s3, file_content, **kwargs)
    # elif file_type == "html":
    #     res = process_html(file_content, **kwargs)
    # elif file_type == "doc":
    #     res = process_doc(s3, **kwargs)
    # elif file_type == "md":
    #     res = process_md(file_content, **kwargs)
    # elif file_type == "image":
    #     process_image(s3, file_content, **kwargs)
    # elif file_type == "json":
    #     res = process_json(file_content, **kwargs)
    # elif file_type == 'jsonl':
    #     res = process_jsonl(s3, file_content, **kwargs)
    return res

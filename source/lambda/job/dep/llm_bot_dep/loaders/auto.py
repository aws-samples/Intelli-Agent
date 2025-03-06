
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


def cb_process_object(file_type: str, file_content, **kwargs):
    res = None
    if file_type == "txt":
        res = process_text(file_content, **kwargs)
    elif file_type == "csv":
        res = process_csv(**kwargs)
    elif file_type == "html":
        res = process_html(file_content, **kwargs)
    elif file_type == "doc":
        res = process_doc(**kwargs)
    elif file_type == "md":
        res = process_md(file_content, **kwargs)
    elif file_type == "pdf":
        res = process_pdf(**kwargs)
    elif file_type == "json":
        res = process_json(file_content, **kwargs)
    elif file_type == "jsonl":
        res = process_jsonl(file_content, **kwargs)
    elif file_type == "xlsx":
        res = process_xlsx(**kwargs)
    elif file_type == "image":
        logger.info("process image")
        res = process_image(**kwargs)
    return res

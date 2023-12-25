from llm_bot_dep.loaders.docx import process_doc
from llm_bot_dep.loaders.markdown import process_md
from .text import process_text
from .csv import process_csv
from .html import process_html
from .pdf import process_pdf
from .image import process_image
from .json import process_json
from .jsonl import process_jsonl

import json
import numpy as np
import logging
from llm_bot_dep.build_index import process_shard

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# def process_json(jsonstr: str, max_os_docs_per_put, **kwargs):
#     logger.info("Processing JSON file...")
#     chunks = json.loads(jsonstr)

#     db_shards = (len(chunks) // max_os_docs_per_put) + 1
#     shards = np.array_split(chunks, db_shards)
#     return shards


def cb_process_object(s3, file_type: str, file_content, **kwargs):
    res = None
    if file_type == "txt":
        res = process_text(file_content, **kwargs)
    elif file_type == "csv":
        res = process_csv(s3, file_content, **kwargs)
    elif file_type == "html":
        res = process_html(file_content, **kwargs)
    elif file_type == "doc":
        res = process_doc(s3, **kwargs)
    elif file_type == "md":
        res = process_md(file_content, **kwargs)
    elif file_type == "pdf":
        # res = post_process_pdf(process_pdf(file_content, **kwargs))
        res = process_pdf(s3, file_content, **kwargs)
    elif file_type == "image":
        process_image(s3, file_content, **kwargs)
    elif file_type == "json":
        res = process_json(file_content, **kwargs)
        # shards = process_json(file_content, kwargs["max_os_docs_per_put"])
        # for shard_id, shard in enumerate(shards):
        #     process_shard(
        #         shard,
        #         kwargs["embeddings_model_info_list"],
        #         kwargs["region"],
        #         kwargs["aos_index"],
        #         kwargs["aosEndpoint"],
        #         kwargs["awsauth"],
        #         1,
        #         kwargs["content_type"],
        #         kwargs["max_os_docs_per_put"],
        #     )
    elif file_type == 'jsonl':
        res = process_jsonl(s3, file_content, **kwargs)
    return res

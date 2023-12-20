
import os

import json
import boto3
import logging
import datetime
import subprocess
from pathlib import Path

from paddleocr import PPStructure
from ppocr.utils.utility import check_and_read
from markdownify import markdownify as md
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

table_engine_ch = PPStructure(det_model_dir='weight/ch_PP-OCRv4_det_infer',
                           rec_model_dir='weight/ch_PP-OCRv4_rec_infer',
                           table_model_dir='weight/ch_ppstructure_mobile_v2.0_SLANet_infer',
                           layout_model_dir='weight/picodet_lcnet_x1_0_fgd_layout_cdla_infer',
                           show_log=True, recovery=True, type='structure', lang="ch", use_pdf2docx_api=True)

table_engine_en = PPStructure(det_model_dir='weight/en_PP-OCRv3_det_infer',
                           rec_model_dir='weight/en_PP-OCRv4_rec_infer',
                           table_model_dir='weight/en_ppstructure_mobile_v2.0_SLANet_infer',
                           layout_model_dir='weight/picodet_lcnet_x1_0_fgd_layout_infer',
                           show_log=True, recovery=True, type='structure', lang="en", use_pdf2docx_api=True)

s3 = boto3.client("s3")

def upload_chunk_to_s3(logger_content: str, bucket: str, prefix: str, splitting_type: str):
    """Upload the logger file to S3 with hierachy below:
    filename A
        ├── before-splitting
        │   ├── timestamp 1
        │   │   ├── logger file 1
        │   ├── timestamp 2
        │   │   ├── logger file 2
        ├── semantic-splitting
        │   ├── timestamp 3
        │   │   ├── logger file 3
        │   ├── timestamp 4
        │   │   ├── logger file 4
        ├── chunk-size-splitting
        │   ├── timestamp 5
        │   │   ├── logger file 5
        │   ├── timestamp 6
        │   │   ├── logger file 6
    filename B
        ├── before-splitting
        │   ├── timestamp 7
        │   │   ├── logger file 7
        │   ├── timestamp 8
        │   │   ├── logger file 8
        ├── semantic-splitting
        │   ├── timestamp 9
        │   │   ├── logger file 9
        │   ├── timestamp 10
        │   │   ├── logger file 10
        ├── chunk-size-splitting
        │   ├── timestamp 11
        │   │   ├── logger file 11
        │   ├── timestamp 12
        │   │   ├── logger file 12
        ...
    """
    # round the timestamp to hours to avoid too many folders
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    # make the logger file name unique
    object_key = f"{prefix}/{splitting_type}/{timestamp}/{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.log"
    try:
        res = s3.put_object(Bucket=bucket, Key=object_key, Body=logger_content)
        logger.info(f"Upload logger file to S3: {res}")
        return object_key
    except Exception as e:
        logger.error(f"Error uploading logger file to S3: {e}")
        return None

def ppstructure_en(file_path: Path) -> str:

    img_list, flag_gif, flag_pdf = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(img_list):
        result = table_engine_en(img, img_idx=index)
        if result != []:
            from copy import deepcopy
            from ppstructure.recovery.recovery_to_doc import sorted_layout_boxes
            h, w, _ = img.shape
            result_cp = deepcopy(result)
            result_sorted = sorted_layout_boxes(result_cp, w)
            all_res += result_sorted
    doc = ''
    flag = 1
    for i, region in enumerate(all_res):
        if len(region['res']) == 0:
            continue
        if flag == 2 and region['layout'] == 'single':
            flag = 1
        elif flag == 1 and region['layout'] == 'double':
            flag = 2
        img_idx = region['img_idx']
        if region['type'].lower() == 'figure':
            continue
        elif region['type'].lower() == 'title':
            doc += '## ' + region['res'][0]['text'] + '\n\n'
        elif region['type'].lower() == 'table':
            doc += md(region['res']['html'], strip=['b', 'img'], heading_style='ATX', newline_style='BACKSLASH')+ '\n\n'
        elif region['type'].lower() in ('header', 'footer'):
            continue
        else:
            for i, line in enumerate(region['res']):
                doc += line['text'] + ' '
        doc += '\n\n'
    doc = re.sub('\n{2,}', '\n\n', doc.strip())
    return doc

def ppstructure_ch(file_path: Path) -> str:

    img_list, flag_gif, flag_pdf = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(img_list):
        result = table_engine_ch(img, img_idx=index)
        if result != []:
            from copy import deepcopy
            from ppstructure.recovery.recovery_to_doc import sorted_layout_boxes
            h, w, _ = img.shape
            result_cp = deepcopy(result)
            result_sorted = sorted_layout_boxes(result_cp, w)
            all_res += result_sorted
    doc = ''
    flag = 1
    for i, region in enumerate(all_res):
        if len(region['res']) == 0:
            continue
        if flag == 2 and region['layout'] == 'single':
            flag = 1
        elif flag == 1 and region['layout'] == 'double':
            flag = 2
        img_idx = region['img_idx']
        if region['type'].lower() == 'figure':
            continue
        elif region['type'].lower() == 'title':
            doc += '## ' + region['res'][0]['text'] + '\n\n'
        elif region['type'].lower() == 'table':
            doc += md(region['res']['html'], strip=['b', 'img'], heading_style='ATX', newline_style='BACKSLASH')+ '\n\n'
        elif region['type'].lower() in ('header', 'footer'):
            continue
        else:
            for i, line in enumerate(region['res']):
                doc += line['text'] + ' '
        doc += '\n\n'
    doc = re.sub('\n{2,}', '\n\n', doc.strip())
    return doc

def process_pdf(bucket, object_key, destination_bucket, mode = 'ppstructure', lang = 'ch', **kwargs):
    """
    Process a given PDF file and extracts structured information from it.
    
    Args:
        bucket (str): The name of the S3 bucket where the PDF file is located.
        object_key (str): The key of the PDF file in the S3 bucket.
        destination_bucket (str): The name of the S3 bucket where the output should be uploaded.
        mode (str): The mode of processing. Can be either `unstructured` or `nougat`.
        
    Returns:
        str: The S3 prefix where the output is located.
    """

    local_path = str(os.path.basename(object_key))
    local_path = f"/tmp/{local_path}"
    file_path = Path(local_path)
    # download to local for futher processing
    logger.info(f"Downloading {object_key} to {local_path}")
    s3.download_file(Bucket=bucket, Key=object_key, Filename=local_path)

    if lang == 'en':
        content = ppstructure_en(local_path)
    else:
        content = ppstructure_ch(local_path)

    # write content to local markdown
    output_path = Path("/home/ubuntu/icyxu/code/AWSLLMCode/llm-bot/tmp_deploy/etl_endpoint/test_result") / f"{file_path.stem}.md"
    with output_path.open("w") as f:
        f.write(content)
    
    filename = file_path.stem
    destination_s3_path = upload_chunk_to_s3(content, destination_bucket, filename, "before-splitting")

    return destination_s3_path


def process_pdf_pipeline(body):
    
    bucket = body["s3_bucket"]
    object_key = body["object_key"]
    destination_bucket = body["destination_bucket"]
    mode = body.get("mode", 'ppstructure')
    lang = body.get("lang", 'ch')
    use_pdf2docx_api = body.get("use_pdf2docx_api", False)

    logging.info(f"Processing bucket: {bucket}, object_key: {object_key}")

    destination_prefix = process_pdf(bucket, object_key, destination_bucket, mode, lang)

    result = {
        "destination_prefix": destination_prefix
    }

    return result


if __name__ == "__main__":
    body = {
        "s3_bucket": "icyxu-llm-glue-assets",
        "object_key": "test_data/test_glue_lib/cn_pdf/2023.ccl-2.6.pdf",
        "destination_bucket": "llm-bot-document-results-icyxu",
        "mode": "ppstructure",
        "lang": "ch",
    }

    process_pdf_pipeline(body)
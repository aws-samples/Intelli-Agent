
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

table_engine = PPStructure(det_model_dir='weight/ch_PP-OCRv4_det_infer',
                           rec_model_dir='weight/ch_PP-OCRv4_rec_infer',
                           table_model_dir='weight/ch_ppstructure_mobile_v2.0_SLANet_infer',
                           layout_model_dir='weight/picodet_lcnet_x1_0_fgd_layout_cdla_infer',
                           show_log=True, recovery=True, type='structure')

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

def nougat(file_path: Path) -> str:
    """Executes the `nougat` command to convert the specified PDF file to Markdown format.

    Args:
        file_path (Path): The path to the PDF file to be converted.

    Returns:
        str: The Markdown content resulting from the `nougat` conversion.
    """
    # nougat ./paperSnapshot.pdf --full-precision --markdown -m 0.1.0-base -o tmp --recompute
    cli_command = ["nougat", str(file_path), "full-precision", "--markdown", "-m", "0.1.0-base", "-o", "/tmp", "--recompute"]

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


def ppstructure(file_path: Path) -> str:

    img_list, flag_gif, flag_pdf = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(img_list):
        result = table_engine(img, img_idx=index)
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

def process_pdf(bucket, object_key, destination_bucket, mode = 'unstructured', **kwargs):
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

    if mode == 'nougat':
        nougat(local_path)
        # Rest of your code for reading and processing the output
        output_path = Path("/tmp") / f"{file_path.stem}.mmd"
        with output_path.open("r") as f:
            content = f.read()
    else:
        content = ppstructure(local_path)

        # write content to local markdown
        # output_path = Path("/home/ubuntu/icyxu/code/AWSLLMCode/llm-bot/tmp_deploy/etl_endpoint/test_result") / f"{file_path.stem}.md"
        # with output_path.open("w") as f:
        #     f.write(content)
    
    filename = file_path.stem
    destination_s3_path = upload_chunk_to_s3(content, destination_bucket, filename, "before-splitting")

    return destination_s3_path


def process_pdf_pipeline(body):
    
    bucket = body["s3_bucket"]
    object_key = body["object_key"]
    destination_bucket = body["destination_bucket"]
    mode = body["mode"]

    logging.info(f"Processing bucket: {bucket}, object_key: {object_key}")

    destination_prefix = process_pdf(bucket, object_key, destination_bucket, mode)

    result = {
        "destination_prefix": destination_prefix
    }

    return result


if __name__ == "__main__":
    body = {
        "s3_bucket": "icyxu-llm-glue-assets",
        "object_key": "test_data/test_glue_lib/cn_pdf/test_pdf_1122/E1 用户手册.pdf",
        "destination_bucket": "llm-bot-dev-apistacknested-llmbotdocumentse383ebd9-xglohd46f8by",
        "mode": "nougat"
    }

    process_pdf_pipeline(body)
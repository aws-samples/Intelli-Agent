import datetime
import json
import logging
import os
import re
import subprocess
from pathlib import Path

import boto3
import layout_predictor_patches
import numpy as np
from markdownify import markdownify as md
from paddleocr import PPStructure
from ppocr.utils.utility import check_and_read
from xycut import recursive_xy_cut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

table_engine_zh = PPStructure(
    det_model_dir="weight/ch_PP-OCRv4_det_infer",
    rec_model_dir="weight/ch_PP-OCRv4_rec_infer",
    table_model_dir="weight/ch_ppstructure_mobile_v2.0_SLANet_infer",
    layout_model_dir="weight/picodet_lcnet_x1_0_fgd_layout_cdla_infer",
    show_log=True,
    recovery=True,
    type="structure",
    lang="ch",
    use_pdf2docx_api=True,
)

table_engine_en = PPStructure(
    det_model_dir="weight/en_PP-OCRv3_det_infer",
    rec_model_dir="weight/en_PP-OCRv4_rec_infer",
    table_model_dir="weight/en_ppstructure_mobile_v2.0_SLANet_infer",
    layout_model_dir="weight/picodet_lcnet_x1_0_fgd_layout_infer",
    show_log=True,
    recovery=True,
    type="structure",
    lang="en",
    use_pdf2docx_api=True,
)


layout_predictor = layout_predictor_patches.LayoutPredictor(
    "weight/picodet_lcnet_x1_0_fgd_layout_cdla_infer"
)
table_engine_zh.layout_predictor = layout_predictor
table_engine_en.layout_predictor = layout_predictor

s3 = boto3.client("s3")


def upload_chunk_to_s3(
    logger_content: str, bucket: str, prefix: str, splitting_type: str
):
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
        logger.info("Upload logger file to S3: %s", res)
        return object_key
    except Exception as e:
        logger.error("Error uploading logger file to S3: %s", e)
        return None


def remove_symbols(text):
    """
    Removes symbols from the given text using regular expressions.

    Args:
        text (str): The input text.

    Returns:
        str: The cleaned text with symbols removed.
    """
    cleaned_text = re.sub(r"[^\w\s\u4e00-\u9fff]", "", text)
    return cleaned_text


def ppstructure_en(file_path: Path) -> str:
    """
    Extracts structured information from images in the given file path and returns a formatted document.

    Args:
        file_path (Path): The path to the file containing the images.

    Returns:
        str: The formatted document containing the extracted information.
    """

    # img_list, flag_gif, flag_pdf are returned from check_and_read
    img_list, _, _ = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(img_list):
        result = table_engine_en(img, img_idx=index)
        if result != []:
            boxes = [row["bbox"] for row in result]
            res = []
            recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
            result_sorted = [result[idx] for idx in res]
            all_res += result_sorted
    doc = ""
    prev_region_text = ""

    for _, region in enumerate(all_res):
        if len(region["res"]) == 0:
            continue
        if region["type"].lower() == "figure":
            region_text = ""
            for _, line in enumerate(region["res"]):
                region_text += line["text"]
        elif region["type"].lower() == "title":
            region_text = ''
            for i, line in enumerate(region['res']):
                region_text += line['text'] + ''
            if remove_symbols(region_text) != remove_symbols(prev_region_text):
                doc += '## ' + region_text + '\n\n'
                prev_region_text = region_text
        elif region["type"].lower() == "table":
            if "<thead>" not in region["res"]["html"]:
                region["res"]["html"] = (
                    region["res"]["html"]
                    .replace("<tr>", "<thead><tr>", 1)
                    .replace("</tr>", "</thead></tr>", 1)
                )
            doc += (
                md(
                    region["res"]["html"],
                    strip=["b", "img"],
                    heading_style="ATX",
                    newline_style="BACKSLASH",
                )
                + "\n\n"
            )
        elif region["type"].lower() in ("header", "footer"):
            continue
        else:
            region_text = ""
            for _, line in enumerate(region["res"]):
                region_text += line["text"] + " "
            if remove_symbols(region_text) != remove_symbols(prev_region_text):
                doc += region_text
                prev_region_text = region_text

        doc += "\n\n"
    doc = re.sub("\n{2,}", "\n\n", doc.strip())
    return doc


def ppstructure_zh(file_path: Path) -> str:
    """
    Extracts structured information from an image file using OCR and returns a formatted document.

    Args:
        file_path (Path): The path to the image file.

    Returns:
        str: The formatted document containing the extracted information.
    """

    # img_list, flag_gif, flag_pdf are returned from check_and_read
    img_list, _, _ = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(img_list):
        result = table_engine_zh(img, img_idx=index)
        if result != []:
            boxes = [row["bbox"] for row in result]
            res = []
            recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
            result_sorted = [result[idx] for idx in res]
            all_res += result_sorted
    doc = ""
    prev_region_text = ""

    for _, region in enumerate(all_res):
        if len(region["res"]) == 0:
            continue

        if region["type"].lower() == "figure":
            region_text = ""
            for _, line in enumerate(region["res"]):
                region_text += line["text"]
        elif region["type"].lower() == "title":
            region_text = ''
            for i, line in enumerate(region['res']):
                region_text += line['text'] + ''
            if remove_symbols(region_text) != remove_symbols(prev_region_text):
                doc += '## ' + region_text + '\n\n'
                prev_region_text = region_text
        elif region["type"].lower() == "table":
            if "<thead>" not in region["res"]["html"]:
                region["res"]["html"] = (
                    region["res"]["html"]
                    .replace("<tr>", "<thead><tr>", 1)
                    .replace("</tr>", "</thead></tr>", 1)
                )
            doc += (
                md(
                    region["res"]["html"],
                    strip=["b", "img"],
                    heading_style="ATX",
                    newline_style="BACKSLASH",
                )
                + "\n\n"
            )
        elif region["type"].lower() in ("header", "footer"):
            continue
        else:
            region_text = ""
            for _, line in enumerate(region["res"]):
                region_text += line["text"]
            if remove_symbols(region_text) != remove_symbols(prev_region_text):
                doc += region_text
                prev_region_text = region_text

        doc += "\n\n"

    doc = re.sub("\n{2,}", "\n\n", doc.strip())
    return doc


def process_pdf(
    bucket, object_key, destination_bucket, mode="ppstructure", lang="zh", **kwargs
):
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
    logger.info("Downloading %s to %s", object_key, local_path)
    s3.download_file(Bucket=bucket, Key=object_key, Filename=local_path)

    if lang == "en":
        content = ppstructure_en(local_path)
    else:
        content = ppstructure_zh(local_path)

    filename = file_path.stem
    destination_s3_path = upload_chunk_to_s3(
        content, destination_bucket, filename, "before-splitting"
    )

    return destination_s3_path


def process_pdf_pipeline(request_body):
    """
    Process PDF pipeline.

    Args:
        request_body (dict): The request body containing the following keys:
            - s3_bucket (str): The source S3 bucket name.
            - object_key (str): The key of the PDF object in the source bucket.
            - destination_bucket (str): The destination S3 bucket name.
            - mode (str, optional): The processing mode. Defaults to "ppstructure".
            - lang (str, optional): The language of the PDF. Defaults to "zh".

    Returns:
        dict: The result of the pipeline containing the following key:
            - destination_prefix (str): The prefix of the processed PDF in the destination bucket.
    """
    bucket = request_body["s3_bucket"]
    object_key = request_body["object_key"]
    destination_bucket = request_body["destination_bucket"]
    mode = request_body.get("mode", "ppstructure")
    lang = request_body.get("lang", "zh")

    logging.info("Processing bucket: %s, object_key: %s", bucket, object_key)

    destination_prefix = process_pdf(bucket, object_key, destination_bucket, mode, lang)

    result = {"destination_prefix": destination_prefix}

    return result


if __name__ == "__main__":
    body = {
        "s3_bucket": "icyxu-llm-glue-assets",
        "object_key": "test_data/test_glue_lib/cn_pdf/2023.ccl-2.6.pdf",
        "destination_bucket": "llm-bot-document-results-icyxu",
        "mode": "ppstructure",
        "lang": "zh",
    }

    print(process_pdf_pipeline(body))

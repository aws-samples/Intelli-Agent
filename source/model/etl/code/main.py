import boto3
import datetime
import json
import logging
import os
import re
import subprocess
from pathlib import Path

from ocr import TextSystem
from table import TableSystem
from layout import LayoutPredictor
import numpy as np
from markdownify import markdownify as md
from utils import check_and_read
from xycut import recursive_xy_cut
import time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StructureSystem(object):
    def __init__(self):
        self.mode = 'structure'
        self.recovery = True
        drop_score = 0
        # init model
        self.layout_predictor = LayoutPredictor()
        self.text_system = TextSystem()
        self.table_system = TableSystem(
            self.text_system.text_detector,
            self.text_system.text_recognizer)
    def __call__(self, img, return_ocr_result_in_table=False, lang='ch'):
        time_dict = {
            'image_orientation': 0,
            'layout': 0,
            'table': 0,
            'table_match': 0,
            'det': 0,
            'rec': 0,
            'kie': 0,
            'all': 0
        }
        if lang == 'zh':
            lang = 'ch'
        start = time.time()
        ori_im = img.copy()
        layout_res, elapse = self.layout_predictor(img)
        time_dict['layout'] += elapse
        res_list = []
        for region in layout_res:
            res = ''
            if region['bbox'] is not None:
                x1, y1, x2, y2 = region['bbox']
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                x1, y1, x2, y2 = max(x1, 0), max(y1, 0), max(x2, 0), max(y2, 0)
                roi_img = ori_im[y1:y2, x1:x2, :]
            else:
                x1, y1, x2, y2 = 0, 0, w, h
                roi_img = ori_im
            if region['label'] == 'table':
                res, table_time_dict = self.table_system(
                    roi_img, return_ocr_result_in_table, lang)
                time_dict['table'] += table_time_dict['table']
                time_dict['table_match'] += table_time_dict['match']
                time_dict['det'] += table_time_dict['det']
                time_dict['rec'] += table_time_dict['rec']
            else:
                wht_im = np.ones(ori_im.shape, dtype=ori_im.dtype)
                wht_im[y1:y2, x1:x2, :] = roi_img
                filter_boxes, filter_rec_res = self.text_system(
                    wht_im, lang)

                # remove style char,
                # when using the recognition model trained on the PubtabNet dataset,
                # it will recognize the text format in the table, such as <b>
                style_token = [
                    '<strike>', '<strike>', '<sup>', '</sub>', '<b>',
                    '</b>', '<sub>', '</sup>', '<overline>',
                    '</overline>', '<underline>', '</underline>', '<i>',
                    '</i>'
                ]
                res = []
                for box, rec_res in zip(filter_boxes, filter_rec_res):
                    rec_str, rec_conf = rec_res
                    for token in style_token:
                        if token in rec_str:
                            rec_str = rec_str.replace(token, '')
                    if not self.recovery:
                        box += [x1, y1]
                    res.append({
                        'text': rec_str,
                        'confidence': float(rec_conf),
                        'text_region': box.tolist()
                    })
            res_list.append({
                'type': region['label'].lower(),
                'bbox': [x1, y1, x2, y2],
                'img': roi_img,
                'res': res,
            })
        end = time.time()
        time_dict['all'] = end - start
        return res_list, time_dict

structure_engine = StructureSystem()

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


def structure_predict(file_path: Path, lang: str) -> str:
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
        result, _ = structure_engine(img, lang=lang)
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

    content = structure_predict(local_path, lang)
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
        "lang": "ch",
    }
    print(process_pdf_pipeline(body))

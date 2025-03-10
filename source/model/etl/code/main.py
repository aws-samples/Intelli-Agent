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
from figure_llm import figureUnderstand
from xycut import recursive_xy_cut
import time
from PIL import Image
import cv2
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIN_TEXT_COUNT = 2  # 最小文本行数量阈值
MAX_SCALE = 4.0  # 最大放大倍数
MAX_PIXELS = 2000 * 3000  # 最大像素数

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
    def __call__(self, img, return_ocr_result_in_table=False, lang='ch', auto_dpi=False):
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
        ori_im_shape = img.shape
        ori_im_dtype = img.dtype
        layout_res, elapse = self.layout_predictor(img)
        final_s = None
        if auto_dpi:
            final_s = 0
            height_limit = 18 if lang == "ch" else 15
            original_h, original_w = img.shape[:2]
            
            for scale_base in [1, 0.66, 0.33]:
                img_cur_scale = cv2.resize(
                    img, (None, None), fx=scale_base, fy=scale_base
                )
                temp_result = self.text_system.text_detector[lang](
                    img_cur_scale, scale=1
                )
                
                # 确保有足够的文本行
                if len(temp_result) < MIN_TEXT_COUNT:
                    continue
                    
                height_list = [
                    max(text_line[:, 1]) - min(text_line[:, 1])
                    for text_line in temp_result
                ]
                height_list.sort()
                
                # 使用95%分位数而不是中位数
                percentile_95_idx = int(len(height_list) * 0.05)
                min_text_line_h = max(
                    height_list[percentile_95_idx],  # 取文本行高度的一半作为下限，避免异常值影响
                    height_limit / MAX_SCALE  # 限制最大缩放比例
                )
                # 计算初始缩放比例
                scale = min((height_limit / min_text_line_h) * scale_base, MAX_SCALE)
                
                # 检查放大后的总像素数是否超过限制
                scaled_pixels = int(original_h * scale) * int(original_w * scale)
                if scaled_pixels > MAX_PIXELS:
                    # 如果超过限制，调整缩放比例
                    max_allowed_scale = np.sqrt(MAX_PIXELS / (original_h * original_w))
                    scale = min(scale, max_allowed_scale)
                
                if scale > final_s:
                    final_s = scale
        time_dict['layout'] += elapse
        res_list = []
        for region in layout_res:
            res = ''
            if region['bbox'] is not None:
                x1, y1, x2, y2 = region['bbox']
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                x1, y1, x2, y2 = max(x1, 0), max(y1, 0), max(x2, 0), max(y2, 0)
                roi_img = img[y1:y2, x1:x2, :]
            else:
                x1, y1, x2, y2 = 0, 0, w, h
                roi_img = img
            if region['label'] == 'table':
                res, table_time_dict = self.table_system(
                    roi_img, return_ocr_result_in_table, lang)
                time_dict['table'] += table_time_dict['table']
                time_dict['table_match'] += table_time_dict['match']
                time_dict['det'] += table_time_dict['det']
                time_dict['rec'] += table_time_dict['rec']
            else:
                wht_im = np.ones(ori_im_shape, dtype=ori_im_dtype)
                wht_im[y1:y2, x1:x2, :] = roi_img
                top = min(y2-y1, y1)
                left = min(x2-x1, x1)
                cur_wht_im = wht_im[y1-top:min(y2+(y2-y1), wht_im.shape[0]), x1-left:min(x2+(x2-x1), wht_im.shape[1])]
                filter_boxes, filter_rec_res = self.text_system(
                    cur_wht_im, lang, final_s)

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
                        box += [x1+left, y1+top]
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
figure_understand = figureUnderstand()
s3 = boto3.client("s3")


def upload_images_to_s3(
    images, bucket: str, prefix: str, splitting_type: str
):
    # round the timestamp to hours to avoid too many folders
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    # make the logger file name unique
    name_s3path = {}
    for key,image in images.items():
        object_key = f"{prefix}/{splitting_type}/{timestamp}/{key.replace('.jpg', '-'+datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')+'.jpg')}"
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            buffer.seek(0)
            res = s3.put_object(Bucket=bucket, Key=object_key, Body=buffer, ContentType='image/jpeg')
        except Exception as e:
            continue
        name_s3path[key] = f'{object_key}'
    return name_s3path


def upload_chunk_to_s3(
    logger_content: str, bucket: str, prefix: str, splitting_type: str
):
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


def structure_predict(file_path: Path, lang: str, auto_dpi, figure_rec) -> str:
    """
    Extracts structured information from images in the given file path and returns a formatted document.

    Args:
        file_path (Path): The path to the file containing the images.

    Returns:
        str: The formatted document containing the extracted information.
    """

    # img_list, flag_gif, flag_pdf are returned from check_and_read
    #img_list, _, _ = check_and_read(file_path)

    all_res = []
    for index, img in enumerate(check_and_read(file_path)):
        result, _ = structure_engine(img, lang=lang, auto_dpi=auto_dpi)
        if result != []:
            boxes = [row["bbox"] for row in result]
            res = []
            recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
            result_sorted = [result[idx] for idx in res]
            all_res += result_sorted
    doc = ""
    prev_region_text = ""
    figure = {}
    for _, region in enumerate(all_res):
        if len(region["res"]) == 0:
            continue
        if region["type"].lower() == "figure":
            region_text = ""
            if figure_rec:
                doc += '<{{figure_' + str(len(figure)) + '}}>\n'
                figure['<{{figure_' + str(len(figure)) + '}}>'] = [Image.fromarray(region["img"][:,:,::-1]), None]
            else:
                doc += '<{{figure_' + str(len(figure)) + '}}>\n'
                for _, line in enumerate(region["res"]):
                    region_text += line["text"] + " "
                if remove_symbols(region_text) != remove_symbols(prev_region_text):
                    figure['<{{figure_' + str(len(figure)) + '}}>'] = [Image.fromarray(region["img"][:,:,::-1]), region_text]
                    prev_region_text = region_text
                else:
                    figure['<{{figure_' + str(len(figure)) + '}}>'] = [Image.fromarray(region["img"][:,:,::-1]), None]
            
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
        else:
            region_text = ""
            for _, line in enumerate(region["res"]):
                region_text += line["text"] + " "
            if remove_symbols(region_text) != remove_symbols(prev_region_text):
                doc += region_text
                prev_region_text = region_text

        doc += "\n\n"
    doc = re.sub("\n{2,}", "\n\n", doc.strip())
    images = {}
    for figure_idx, (k,v) in enumerate(figure.items()):
        images[f'{figure_idx:05d}.jpg'] = v[0]
        region_text = v[1] if not v[1] is None else ''
        if figure_rec:
            start_pos = doc.index(k)
            context = doc[max(start_pos-200, 0): min(start_pos+200, len(doc))]
            doc = doc.replace(k, figure_understand(v[0], context, k, s3_link=f'{figure_idx:05d}.jpg'))
        else:
            doc = doc.replace(k, f"\n<figure>\n<link>{figure_idx:05d}.jpg</link>\n<type>ocr</type>\n<desp>\n{region_text}\n</desp>\n</figure>\n")
    doc = re.sub("\n{2,}", "\n\n", doc.strip())
    return doc, images

def process_pdf_pipeline(request_body):
    """
    Process PDF pipeline.

    Args:
        request_body (dict): The request body containing the following keys:
            - s3_bucket (str): The source S3 bucket name.
            - object_key (str): The key of the PDF object in the source bucket.
            - destination_bucket (str): The destination S3 bucket name.
            - portal_bucket (str): The portal S3 bucket name
            - mode (str, optional): The processing mode. Defaults to "ppstructure".
            - lang (str, optional): The language of the PDF. Defaults to "zh".

    Returns:
        dict: The result of the pipeline containing the following key:
            - destination_prefix (str): The prefix of the processed PDF in the destination bucket.
    """
    bucket = request_body["s3_bucket"]
    object_key = request_body["object_key"]
    destination_bucket = request_body["destination_bucket"]
    portal_bucket = request_body["portal_bucket"]
    mode = request_body.get("mode", "ppstructure")
    lang = request_body.get("lang", "zh")
    auto_dpi = bool(request_body.get("auto_dpi", True))
    figure_rec = bool(request_body.get("figure_recognition", True))
    logging.info("Processing bucket: %s, object_key: %s", bucket, object_key)
    local_path = str(os.path.basename(object_key))
    local_path = f"/tmp/{local_path}"
    file_path = Path(local_path)
    logger.info("Downloading %s to %s", object_key, local_path)
    s3.download_file(Bucket=bucket, Key=object_key, Filename=local_path)

    content, images = structure_predict(local_path, lang, auto_dpi, figure_rec)
    filename = file_path.stem
    name_s3path = upload_images_to_s3(
        images, portal_bucket, filename, "image"
    )
    for key, s3_path in name_s3path.items():
        content = content.replace(f'<link>{key}</link>', f'<link>{s3_path}</link>')
    destination_s3_path = upload_chunk_to_s3(
        content, destination_bucket, filename, "before-splitting"
    )
    
    result = {"destination_prefix": destination_s3_path}

    return result
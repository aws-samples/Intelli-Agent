#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import cv2
import logging
import numpy as np
from PIL import Image
from io import BytesIO
import boto3
import base64
try:
    import urllib.request as urllib2
    from urllib.parse import urlparse
except ImportError:
    import urllib2
    from urlparse import urlparse

__all__ = [
    "check_and_read",
    "readimg",
    "lambda_return"
]

def check_and_read(img_path):
    """Check and read image file in different formats.
    
    Supports:
    - Common image formats (JPG, PNG, etc.): Returns the image
    - GIF: Returns first frame
    - PDF: Returns generator of all pages as images
    
    Args:
        img_path: Path to the image file
        
    Returns:
        Tuple of (image_data, is_valid, is_gif)
        For PDFs, returns a generator of images
    """
    # Get file extension
    ext = os.path.basename(img_path)[-3:].lower()
    # Handle GIF files
    if ext == "gif":
        gif = cv2.VideoCapture(img_path)
        ret, frame = gif.read()
        if not ret:
            logger = logging.getLogger("ppocr")
            logger.info("Cannot read {}. This gif image maybe corrupted.")
            return None, False
        if len(frame.shape) == 2 or frame.shape[-1] == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        imgvalue = frame[:, :, ::-1]
        yield imgvalue
        
    # Handle PDF files
    elif ext == "pdf":
        import fitz
        MAX_PIXELS = 6000000  # 最大像素数限制
        with fitz.open(img_path) as pdf:
            for pg in range(0, pdf.page_count):
                page = pdf[pg]
                rect = page.rect
                w, h = rect.width, rect.height
                scale = min(1.0, np.sqrt(MAX_PIXELS / (w * h * 9)))  # 9是因为原来的Matrix(3, 3)
                mat = fitz.Matrix(3 * scale, 3 * scale)
                pm = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                yield img
    # Handle common image formats (JPG, PNG, etc.)
    else:
        img = cv2.imread(img_path)
        if img is None:
            return None
        if len(img.shape) == 2 or img.shape[-1] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        yield img[:, :, ::-1]

def readimg(body, keys=None):
    """Read images from various sources in a request body.
    
    Supports:
    - HTTP URLs
    - S3 URLs
    - Base64 encoded images
    
    Args:
        body: Request body containing image data
        keys: Keys to look for in the body. If None, uses all keys
        
    Returns:
        Dict mapping keys to numpy arrays of images
    """
    if keys is None:
        keys = body.keys()
    inputs = dict()
    for key in keys:
        try:
            if key.startswith('url'): # url形式
                if body[key].startswith('http'): # http url
                    image_string = urllib2.urlopen(body[key]).read()
                elif body[key].startswith('s3'): # s3 key
                    o = urlparse(body[key])
                    bucket = o.netloc
                    path = o.path.lstrip('/')
                    s3 = boto3.resource('s3')
                    img_obj = s3.Object(bucket, path)
                    image_string = img_obj.get()['Body'].read()
                else:
                    raise
            elif key.startswith('img'): # base64形式
                image_string = base64.b64decode(body[key])
            else:
                raise
            inputs[key] = np.array(Image.open(BytesIO(image_string)).convert('RGB'))[:, :, :3]
        except:
            inputs[key] = None
    return inputs

def lambda_return(statusCode, body):
    """Create a standardized Lambda function response.
    
    Args:
        statusCode: HTTP status code
        body: Response body
        
    Returns:
        Dict containing the Lambda response structure
    """
    return {
        'statusCode': statusCode,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': body
    } 
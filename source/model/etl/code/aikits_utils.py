from io import BytesIO
import boto3
import base64
import numpy as np
from PIL import Image
import cv2
try:
    import urllib.request as urllib2
    from urllib.parse import urlparse
except ImportError:
    import urllib2
    from urlparse import urlparse
    
def readimg(body, keys=None):
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
    return {
        'statusCode': statusCode,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': body
    }
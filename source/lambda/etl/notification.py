import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
execution_table = dynamodb.Table(os.environ.get('EXECUTION_TABLE'))


def lambda_handler(event, context):
    logger.info(f"event:{event}")
    


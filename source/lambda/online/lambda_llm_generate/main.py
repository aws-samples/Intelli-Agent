import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging
import time
import uuid

import boto3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from utils.constant import Type

from utils.ddb_utils import DynamoDBChatMessageHistory
from utils.online_entries import get_entry

# @handle_error
def lambda_handler(event, context):
    request_timestamp = time.time()

    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}

    llmbot_response = {
        'answer': 'fake test for graph logic',
    }

    # resp_header = {
    #     "Content-Type": "application/json",
    #     "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    #     "Access-Control-Allow-Origin": "*",
    #     "Access-Control-Allow-Methods": "*",
    # }
    # if get_contexts:
    #     llmbot_response["contexts"] = contexts
    # if enable_debug:
    #     debug_info["contexts"] = contexts
    #     llmbot_response["debug_info"] = debug_info
    response["body"] = llmbot_response

    print(f"finish llm generate lambda invoke")
    return response
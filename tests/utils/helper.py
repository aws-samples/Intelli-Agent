import decimal
import io
import json
import logging
import math
import os
import subprocess
import sys
import tarfile

import requests
from utils.api import Api

import config as config

logger = logging.getLogger(__name__)


def upload_file_to_s3(s3_client, file_path, s3_bucket, s3_key):
    s3_client.upload_file(file_path, s3_bucket, s3_key)


def get_knowledge_sources_from_restapi_response_dict(response_dict):
    knowledge_sources = response_dict["choices"][-1]["message"]["knowledge_sources"]
    return knowledge_sources


def get_knowledge_sources_from_wsapi_context(context_dict):
    knowledge_sources = context_dict["choices"][-1]["knowledge_sources"]
    return knowledge_sources

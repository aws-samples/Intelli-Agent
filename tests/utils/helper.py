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

import logging

import boto3
import pytest
import requests
from utils.helper import upload_file_to_s3

import config as config

s3_client = boto3.client("s3")

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestCommonEntryRestfulApi:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_workspace_pdf():

        # Upload file to S3
        file_path = "data/document/pdf/sdp_overview.pdf"
        s3_bucket = config.api_bucket
        s3_key = f"api_test/{file_path}"
        upload_file_to_s3(s3_client, file_path, s3_bucket, s3_key)

        data = {
            "s3Bucket": bucket,
            "s3Prefix": key,
            "offline": "true",
            "workspaceId": "aos_index_mkt_faq_qq_m3",
            "operationType": "create",
            "indexType": "qq",
        }

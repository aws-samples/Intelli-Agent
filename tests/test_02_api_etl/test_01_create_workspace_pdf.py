import logging
import time
from datetime import datetime, timedelta

import boto3
import pytest
import requests
from utils.api import Api
from utils.enums import EtlStatus
from utils.helper import upload_file_to_s3

import config as config

s3_client = boto3.client("s3")

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestCreateWorkspaceApiPdf:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_01_create_workspace_pdf(self):

        # Upload file to S3
        file_path = "data/document/pdf/sdp_overview.pdf"
        s3_bucket = config.api_bucket
        s3_key = f"api_test/{file_path}"
        upload_file_to_s3(s3_client, file_path, s3_bucket, s3_key)

        data = {
            "s3Bucket": s3_bucket,
            "s3Prefix": s3_key,
            "offline": "true",
            "chatbotId": "llm-bot-test-pdf-workspace",
            "operationType": "create",
        }

        etl_response = self.api.trigger_etl(data=data)
        global etl_execution_id
        etl_execution_id = etl_response.json()["execution_id"]

        print(f"etl_execution_id: {etl_execution_id}")
        assert etl_response.status_code == 200

    def test_10_get_etl_status(self):
        global etl_execution_id
        params = {"executionId": etl_execution_id}
        response = self.api.get_etl_status(params=params)
        assert response.status_code == 200

        timeout = datetime.now() + timedelta(minutes=5)

        while datetime.now() < timeout:
            response = self.api.get_etl_status(params=params)
            response_count = response.json()["Count"]

            if response_count == 0:
                logger.info("No Finished ETL Job Execution found.")
            else:
                status = response.json()["Items"][0]["status"]
                logger.info(f"ETL Job Execution {etl_execution_id} is {status}")
                if status == EtlStatus.SUCCEEDED.value:
                    break
                elif status == EtlStatus.FAILED.value:
                    logger.error(response.dumps())
                    raise Exception(f"ETL Job Execution {etl_execution_id} failed.")
                else:
                    raise Exception(
                        f"ETL Job Execution {etl_execution_id} is still running."
                    )
            time.sleep(10)
        else:
            raise Exception("Inference timed out after 5 minutes.")

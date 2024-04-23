import logging

import boto3
import pytest
import requests
from utils.api import Api

import config as config

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestCommonEntryRestfulApi:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_01_get_etl_status(self):
        data = {
            "aos_index": "llm-bot-test-pdf-workspace-offline",
            "operation": "query_all",
            "body": {},
        }
        response = self.api.query_aos_index(data=data)
        assert response.status_code == 200
        assert response.json()["hits"]["hits"]

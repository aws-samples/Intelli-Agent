import logging

import boto3
import pytest
import requests
from utils.api import WsApi

import config as config

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestCommonEntryWebsocketApi:

    @classmethod
    def setup_class(self):
        self.ws_api = WsApi(config)
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_01_common_entry_restful_api(self):
        # Test case 1: Valid request
        data = {
            "messages": [{"role": "user", "content": "你好"}],
            "type": "common",
            "retriever_config": {"workspace_ids": []},
        }
        answer, context = self.ws_api.qa(data=data)
        assert answer

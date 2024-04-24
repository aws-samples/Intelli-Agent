import logging

import boto3
import pytest
import requests
from utils.api import WsApi
from utils.helper import get_knowledge_sources_from_wsapi_context

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
            "messages": [
                {
                    "role": "user",
                    "content": "How can sensitive data protection solution help customers?",
                }
            ],
            "type": "common",
            "retriever_config": {"workspace_ids": ["llm-bot-test-pdf-workspace"]},
        }
        answer, context = self.ws_api.qa(data=data)
        knowledge_sources = get_knowledge_sources_from_wsapi_context(context)
        assert answer
        assert (
            f"s3://{config.api_bucket}/api_test/data/document/pdf/sdp_overview.pdf"
            in knowledge_sources
        )

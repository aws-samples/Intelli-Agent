import datetime
import os
import threading
import time
# import api_test.config as config
from dotenv import load_dotenv
import pytest
import requests
import websocket

from api_test.biz_logic.rest_api import openapi_client
# from api_test.biz_logic.rest_api import IntellapiconnnHdtwRWUXa

from .utils import step
import logging
import boto3

logger = logging.getLogger(__name__)
sts = boto3.client('sts')
s3_client = boto3.client('s3')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestChat:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test start..."
        )
        load_dotenv()
        cls.configuration = openapi_client.Configuration(host=os.getenv('api_url'))
        cls.api_client = openapi_client.ApiClient(cls.configuration)
        cls.api_client.set_default_header("Authorization", f'Bearer {os.getenv("token")}')
        cls.api_instance = openapi_client.DefaultApi(cls.api_client)
        globals()["exe_ids"] = None

    @classmethod
    def teardown_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test end."
        )
    
    def on_message(ws, message):
        ws.received_message = message

    @pytest.fixture
    def websocket_client(self):
        uri = "ws://localhost:8000/ws"
        ws = websocket.WebSocketApp(uri, on_message=self.on_message)
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
        time.sleep(1)  # Give it a second to connect
        yield ws
        ws.close()
        thread.join()

    def test_websocket(websocket_client):
        ws = websocket_client
        ws.send("Hello, WebSocket!")
        time.sleep(1)  # Give it a second to receive message
        assert ws.received_message == "Hello, Client!"

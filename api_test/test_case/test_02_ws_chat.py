import datetime
import json
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
# sts = boto3.client('sts')
# s3_client = boto3.client('s3')
# caller_identity = boto3.client('sts').get_caller_identity()
# partition = caller_identity['Arn'].split(':')[1]

class TestChat:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test start..."
        )
        load_dotenv()
        cls.request_url=f"{os.getenv('ws_api_url')}?idToken={os.getenv('token')}"
        cls.ws = websocket.WebSocket()
        cls.ws.settimeout(30)
        cls.wait_time = 1
        cls.retry_attempts = 3
        cls.config= {
            "chatbot_config": {
                "chatbot_mode":"agent",
                "default_llm_config":{
                    "model_id":"anthropic.claude-3-sonnet-20240229-v1:0",
                    "model_kwargs": {
                        "temperature": 0.1,
                        "max_tokens": 4096
                    }
                },
                "default_workspace_config": {
                    "intent_workspace_ids": [],
                    "rag_workspace_ids": ["Admin"]
                },
                "goods_id":"751501610432",
                "google_api_key":"",
                "enable_trace": True,
                "use_history": True, # 多轮对话
                "use_websearch": True
        },
        "entry_type":"common",
        "query": "Hi, who are you?",
        "session_id": __name__
        }

    @classmethod
    def teardown_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test end."
        )

    # @pytest.fixture(autouse=True)
    def setup_method(self, method):
        """Setup method to create a WebSocket client connection before each test."""
        logger.info("%s start...", method.__name__)
        self.ws.connect(self.request_url)
        time.sleep(self.wait_time)
    
    def teardown_method(self, method):
        """Teardown method to close the WebSocket client connection after each test."""
        self.ws.close()
        logger.info("%s completed.", method.__name__)

    def test_25_wss_connection(self):
        '''test_25_wss_connection'''
        assert self.ws.connected, "WebSocket connection failed"
    
    def test_26_agent_message_trace_history(self):
        '''test_26_agent_message_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "agent"
        self.ws.send(json.dumps(self.config))
        # for attempt in range(self.retry_attempts):
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_26_agent_message_trace_history failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CONTEXT' for item in messages), "test_26_agent_message_trace_history failed!"

    def test_27_agent_message_no_trace(self):
        '''test_27_agent_message_no_trace'''
        self.config["chatbot_config"]["chatbot_mode"] = "agent"
        self.config["chatbot_config"]["enable_trace"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException as e:
            logger.error(e)
            assert False, "test_27_agent_message_no_trace failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CONTEXT' for item in messages) and all(item["message_type"] != 'MONITOR' for item in messages),"test_27_agent_message_no_trace failed!"

    def test_28_agent_message_no_history(self):
        '''test_28_agent_message_no_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "agent"
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_28_agent_message_no_history failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CONTEXT' for item in messages),"test_28_agent_message_no_history failed!"

    def test_29_agent_message_no_trace_history(self):
        '''test_29_agent_message_no_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "agent"
        self.config["chatbot_config"]["enable_trace"] = False
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_29_agent_message_no_trace_history failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CONTEXT' for item in messages) and all(item["message_type"] != 'MONITOR' for item in messages),"test_29_agent_message_no_trace_history failed!"
    
    def test_30_chat_message_trace_history(self):
        '''test_30_chat_message_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "chat"
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_30_chat_message_trace_history failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CHUNK' for item in messages) and all(item["message_type"] != 'CONTEXT' for item in messages),"test_30_chat_message_trace_history failed!"
    
    def test_31_chat_message_no_trace(self):
        '''test_31_chat_message_no_trace'''
        self.config["chatbot_config"]["chatbot_mode"] = "chat"
        self.config["chatbot_config"]["enable_trace"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_31_chat_message_no_trace failed(TIME_OUT)!"
        logger.info(messages)
        assert any(item["message_type"] == 'CHUNK' for item in messages) and all(item["message_type"] != 'CONTEXT' for item in messages) and all(item["message_type"] != 'MONITOR' for item in messages),"test_31_chat_message_no_trace failed!"

    def test_32_chat_message_no_history(self):
        '''test_32_chat_message_no_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "chat"
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_32_chat_message_no_history failed(TIME_OUT)!"
        logger.info(messages)
        assert any(item["message_type"] == 'MONITOR' for item in messages) and any(item["message_type"] == 'CHUNK' for item in messages),"test_32_chat_message_no_history failed!"

    def test_33_chat_message_no_trace_history(self):
        '''test_33_chat_message_no_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "chat"
        self.config["chatbot_config"]["enable_trace"] = False
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_33_chat_message_no_trace_history failed(TIME_OUT)!"
        logger.info(messages)
        assert all(item["message_type"] != 'MONITOR' for item in messages),"test_33_chat_message_no_trace_history failed!"

    def test_34_rag_message_trace_history(self):
        '''test_34_rag_message_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "rag"
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_34_rag_message_trace_history failed(TIME_OUT)!"
        assert any(item["message_type"] == 'CHUNK' for item in messages) and all(item["message_type"] != 'CONTEXT' for item in messages),"test_34_rag_message_trace_history failed!"
    
    def test_35_rag_message_no_trace(self):
        '''test_35_rag_message_no_trace'''
        self.config["chatbot_config"]["chatbot_mode"] = "rag"
        self.config["chatbot_config"]["enable_trace"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_35_rag_message_no_trace failed(TIME_OUT)!"
        logger.info(messages)
        assert any(item["message_type"] == 'CHUNK' for item in messages) and all(item["message_type"] != 'CONTEXT' for item in messages) and all(item["message_type"] != 'MONITOR' for item in messages),"test_35_rag_message_no_trace failed!"

    def test_36_rag_message_no_history(self):
        '''test_36_rag_message_no_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "rag"
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_36_rag_message_no_history failed(TIME_OUT)!"
        logger.info(messages)
        assert any(item["message_type"] == 'MONITOR' for item in messages) and any(item["message_type"] == 'CHUNK' for item in messages),"test_36_rag_message_no_history failed!"

    def test_37_rag_message_no_trace_history(self):
        '''test_37_rag_message_no_trace_history'''
        self.config["chatbot_config"]["chatbot_mode"] = "rag"
        self.config["chatbot_config"]["enable_trace"] = False
        self.config["chatbot_config"]["use_history"] = False
        self.ws.send(json.dumps(self.config))
        messages=[]
        try:
            while True:
                response = self.ws.recv()
                if response:
                    message = json.loads(response)
                    messages.append(message)
                if message["message_type"] == "END":
                    break
        except websocket.WebSocketTimeoutException:
            assert False, "test_37_rag_message_no_trace_history failed(TIME_OUT)!"
        logger.info(messages)
        assert all(item["message_type"] != 'MONITOR' for item in messages),"test_37_rag_message_no_trace_history failed!"
import json
import logging
import os
from datetime import datetime


import boto3
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import BedrockChat
from langchain_community.llms.sagemaker_endpoint import LineIterator

from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType
)
from common_logic.common_utils.logger_utils import get_logger

AI_MESSAGE_TYPE = MessageType.AI_MESSAGE_TYPE
HUMAN_MESSAGE_TYPE = MessageType.HUMAN_MESSAGE_TYPE
SYSTEM_MESSAGE_TYPE = MessageType.SYSTEM_MESSAGE_TYPE

logger = get_logger("llm_model")



class ModeMixins:
    @staticmethod
    def convert_messages_role(messages:list[dict],role_map:dict):
        """
        Args:
            messages (list[dict]): 
            role_map (dict): {"current_role":"targe_role"}

        Returns:
            _type_: as messages
        """
        valid_roles = list(role_map.keys())
        new_messages = []
        for message in messages:
            message = {**message}
            role = message['role']
            assert role in valid_roles,(role,valid_roles,messages)
            message['role'] = role_map[role]
            new_messages.append(message)
        return new_messages    


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == "Model" or new_cls.model_id is None:
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls


class Model(ModeMixins,metaclass=ModelMeta):
    model_id = None
    model_map = {}

    @classmethod
    def get_model(cls, model_id, model_kwargs=None, **kwargs):
        return cls.model_map[model_id].create_model(model_kwargs=model_kwargs, **kwargs)

# Bedrock model type
class Claude2(Model):
    model_id = LLMModelType.CLAUDE_2
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.7, "top_p": 0.9}

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = (
            kwargs.get("region_name", None)
            or os.environ.get("AWS_REGION", None)
            or None
        )
        llm = BedrockChat(
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )

        return llm


class ClaudeInstance(Claude2):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude21(Claude2):
    model_id = LLMModelType.CLAUDE_21


class Claude3Sonnet(Claude2):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3Haiku(Claude2):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35Sonnet(Claude2):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"


class Mixtral8x7b(Claude2):
    model_id = LLMModelType.MIXTRAL_8X7B_INSTRUCT
    default_model_kwargs = {"max_tokens": 4096, "temperature": 0.01}

# Sagemker Inference type
class SagemakerModelBase(Model):
    default_model_kwargs = None
    content_type = "application/json"
    accepts = "application/json"

    @classmethod
    def create_client(cls, region_name):
        client = boto3.client("sagemaker-runtime", region_name=region_name)
        return client

    def __init__(self, model_kwargs=None, **kwargs) -> None:
        self.model_kwargs = model_kwargs or {}
        if self.default_model_kwargs is not None:
            self.model_kwargs = {**self.default_model_kwargs, **self.model_kwargs}

        self.region_name = (
            kwargs.get("region_name", None)
            or os.environ.get("AWS_REGION", None)
            or None
        )
        self.kwargs = kwargs
        self.endpoint_name = kwargs["endpoint_name"]
        self.client = self.create_client(self.region_name)

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        return cls(model_kwargs=model_kwargs, **kwargs)

    def transform_input(self, x):
        raise NotImplementedError

    def transform_output(self, output):
        response = json.loads(output.read().decode("utf-8"))
        return response

    def _stream(self, x):
        body = self.transform_input(x)
        resp = self.client.invoke_endpoint_with_response_stream(
            EndpointName=self.endpoint_name,
            Body=body,
            ContentType=self.content_type,
        )
        iterator = LineIterator(resp["Body"])
        for line in iterator:
            resp = json.loads(line)
            error_msg = resp.get("error_msg", None)
            if error_msg:
                raise RuntimeError(error_msg)
            resp_output = resp.get("outputs")
            yield resp_output

    def _invoke(self, x):
        body = self.transform_input(x)
        try:
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                Body=body,
                ContentType=self.content_type,
                Accept=self.accepts,
            )
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")
        response = self.transform_output(response["Body"])
        return response

    def invoke(self, x, stream=False):
        x["stream"] = stream
        if stream:
            return self._stream(x)
        else:
            return self._invoke(x)


class Baichuan2Chat13B4Bits(SagemakerModelBase):
    model_id = LLMModelType.BAICHUAN2_13B_CHAT
    # content_handler=Baichuan2ContentHandlerChat()
    default_model_kwargs = {
        "max_new_tokens": 2048,
        "temperature": 0.3,
        "top_k": 5,
        "top_p": 0.85,
        # "repetition_penalty": 1.05,
        "do_sample": True,
        "timeout": 60,
    }

    def transform_input(self, x):
        query = x["query"]
        _chat_history = x["chat_history"]
        _chat_history = [
            {"role": message.type, "content": message.content}
            for message in _chat_history
        ]

        chat_history = []
        for message in _chat_history:
            content = message["content"]
            role = message["role"]
            assert role in [
                MessageType.HUMAN_MESSAGE_TYPE,
                MessageType.AI_MESSAGE_TYPE,
                MessageType.SYSTEM_MESSAGE_TYPE,
            ], f"invalid role: {role}"
            if role == MessageType.AI_MESSAGE_TYPE:
                role = "assistant"
            elif role == MessageType.HUMAN_MESSAGE_TYPE:
                role = "user"

            chat_history.append({"role": role, "content": content})
        _messages = chat_history + [{"role": "user", "content": query}]
        messages = []
        system_messages = []
        for message in _messages:
            if message["role"] == MessageType.SYSTEM_MESSAGE_TYPE:
                system_messages.append(message)
            else:
                messages.append(message)

        if system_messages:
            system_prompt = "\n".join([s["content"] for s in system_messages])
            first_content = messages[0]["content"]
            messages[0]["content"] = f"{system_prompt}\n{first_content}"

        input_str = json.dumps(
            {
                "messages": messages,
                "parameters": {"stream": x["stream"], **self.model_kwargs},
            }
        )
        return input_str


class Internlm2Chat7B(SagemakerModelBase):
    model_id = LLMModelType.INTERNLM2_CHAT_7B
    default_model_kwargs = {
        "max_new_tokens": 1024,
        "timeout": 60,
        # 'repetition_penalty':1.05,
        # "do_sample":True,
        "temperature": 0.1,
        "top_p": 0.8,
    }

    # meta_instruction = "You are a helpful AI Assistant"

    def transform_input(self, x):
        logger.info(f'prompt char num: {len(x["prompt"])}')
        body = {
            "query": x["prompt"],
            # "meta_instruction": x.get('meta_instruction',self.meta_instruction),
            "stream": x["stream"],
            # "history": history
        }
        body.update(self.model_kwargs)
        # print('body',body)
        input_str = json.dumps(body)
        return input_str


class Internlm2Chat20B(Internlm2Chat7B):
    model_id = LLMModelType.INTERNLM2_CHAT_20B


class GLM4Chat9B(SagemakerModelBase):
    model_id = LLMModelType.GLM_4_9B_CHAT
    default_model_kwargs = {
        "max_new_tokens": 1024,
        "timeout": 60,
        "temperature": 0.1,
    }
    role_map={
                MessageType.SYSTEM_MESSAGE_TYPE: 'system',
                MessageType.HUMAN_MESSAGE_TYPE: 'user',
                MessageType.AI_MESSAGE_TYPE: "assistant",
                MessageType.TOOL_MESSAGE_TYPE:  "observation"
            }

    def transform_input(self, x:dict):
        _chat_history = self.convert_messages_role(
            x['chat_history'],
            role_map=self.role_map
        )
        chat_history = []
        for message in _chat_history:
            if message['role'] == "assistant":
                content = message['content']
                if not content.endswith("<|observation|>"):
                    if not content.endswith("<|user|>"):
                        message['content'] = message['content'] + "<|user|>"
            chat_history.append(message)
                
        logger.info(f"glm chat_history: {chat_history}")
        body = {
            "chat_history": chat_history,
            "stream": x["stream"],
            **self.model_kwargs
        }
        input_str = json.dumps(body)
        return input_str

class Qwen2Instruct7B(SagemakerModelBase):
    model_id = LLMModelType.QWEN2INSTRUCT7B
    default_model_kwargs = {
        "max_tokens": 1024,
        "temperature": 0.1,
    }
    role_map={
                MessageType.SYSTEM_MESSAGE_TYPE: 'system',
                MessageType.HUMAN_MESSAGE_TYPE: 'user',
                MessageType.AI_MESSAGE_TYPE: "assistant"
            }

    def transform_input(self, x:dict):
        chat_history = self.convert_messages_role(
            x['chat_history'],
            role_map=self.role_map
        )
        
        body = {
            "chat_history": chat_history,
            "stream": x["stream"],
            **self.model_kwargs
        }
        logger.info(f"qwen body: {body}")
        input_str = json.dumps(body)
        return input_str


class Qwen2Instruct72B(Qwen2Instruct7B):
    model_id = LLMModelType.QWEN2INSTRUCT72B


# ChatGPT model type
class ChatGPT35(Model):
    model_id = "gpt-3.5-turbo-0125"
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.7, "top_p": 0.9}

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = (
            kwargs.get("region_name", None)
            or os.environ.get("AWS_REGION", None)
            or None
        )

        llm = ChatOpenAI(
            model=cls.model_id,
            model_kwargs=model_kwargs,
        )

        return llm

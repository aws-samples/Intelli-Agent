"""
chat models build in command pattern
"""

from common_logic.common_utils.constant import ModelProvider

from ..model_config import ModelConfig
from langchain_openai import ChatOpenAI
ChatOpenAI.stream
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.messages import BaseMessage,BaseMessageChunk
from typing import Iterator,Union
import threading

class ModelMixins:
    @staticmethod
    def convert_messages_role(messages: list[dict], role_map: dict):
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
            role = message["role"]
            assert role in valid_roles, (role, valid_roles, messages)
            message["role"] = role_map[role]
            new_messages.append(message)
        return new_messages


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if (
            name == "Model"
            or new_cls.model_id is None
            or name.endswith("BaseModel")
            or name.lower().endswith("basemodel")
        ):
            return new_cls
        new_cls.model_map[new_cls.get_model_id()] = new_cls
        return new_cls


class Model(ModelMixins, metaclass=ModelMeta):
    model_id: str = None
    model: Union[str,None] = None
    enable_any_tool_choice: bool = True
    enable_prefill: bool = True
    any_tool_choice_value = "any"
    model_map = {}
    model_provider: ModelProvider = ModelProvider.BEDROCK
    is_reasoning_model: bool = False

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_model_id(cls, model_id=None, model_provider=None):
        if model_id is None:
            model_id = cls.model_id
        if model_provider is None:
            model_provider = cls.model_provider
        return f"{model_id}__{model_provider}"

    @classmethod
    def get_model(cls, model_id, model_kwargs=None, **kwargs):
        model_provider = kwargs["provider"]
        # dynamic load module
        _load_module(model_provider)
        model_identify = cls.get_model_id(
            model_id=model_id, model_provider=model_provider
        )
        return cls.model_map[model_identify].create_model(
            model_kwargs=model_kwargs, **kwargs
        )

    @classmethod
    def model_id_to_class_name(cls, model_id: str) -> str:
        """Convert model ID to a valid Python class name.

        Examples:
            anthropic.claude-3-haiku-20240307-v1:0 -> Claude3Haiku20240307V1Model
        """
        # Remove version numbers and vendor prefixes
        name = str(model_id).split(":")[0]
        name = name.split(".")[-1]
        parts = name.replace("_", "-").split("-")

        cleaned_parts = []
        for part in parts:
            if any(c.isdigit() for c in part):
                cleaned = "".join(
                    c.upper() if i == 0 or part[i - 1] in "- " else c
                    for i, c in enumerate(part)
                )
            else:
                cleaned = part.capitalize()
            cleaned_parts.append(cleaned)

        return "".join(cleaned_parts) + "Model"

    @classmethod
    def create_for_model(cls, config: ModelConfig):
        """Factory method to create a model with a specific model id"""
        # config = MODEL_CONFIGS[model_id]
        model_id = config.model_id
        # Create a new class dynamically
        model_class = type(
            f"{cls.model_id_to_class_name(model_id)}",
            (cls,),
            {
                "model_id": model_id,
                "model": config.model,
                "default_model_kwargs": config.default_model_kwargs,
                "enable_any_tool_choice": config.enable_any_tool_choice,
                "enable_prefill": config.enable_prefill,
            },
        )
        return model_class

    @classmethod
    def create_for_models(cls, configs: list[ModelConfig]):
        for config in configs:
            cls.create_for_model(config)


def _import_bedrock_models():
    from . import bedrock_models


def _import_brconnector_bedrock_models():
    from . import bedrock_models


def _import_openai_models():
    from . import openai_models


def _import_dmaa_models():
    from . import dmaa_models


def _import_sagemaker_models():
    from . import sagemaker_models


def _import_siliconflow_models():
    from . import siliconflow_models


def _load_module(model_provider):
    assert model_provider in MODEL_PROVIDER_LOAD_FN_MAP, (
        model_provider,
        MODEL_PROVIDER_LOAD_FN_MAP,
    )
    MODEL_PROVIDER_LOAD_FN_MAP[model_provider]()


MODEL_PROVIDER_LOAD_FN_MAP = {
    ModelProvider.BEDROCK: _import_bedrock_models,
    ModelProvider.BRCONNECTOR_BEDROCK: _import_brconnector_bedrock_models,
    ModelProvider.OPENAI: _import_openai_models,
    ModelProvider.DMAA: _import_dmaa_models,
    ModelProvider.SAGEMAKER: _import_sagemaker_models,
    ModelProvider.SILICONFLOW: _import_siliconflow_models,
}


ChatModel = Model

class ReasonModelResult:
    def __init__(self,
                 ai_message:BaseMessage,
                 think_start_tag="<think>",
                 think_end_tag="</think>",
                 reasoning_content_key="reasoning_content"
        ):
        self.ai_message = ai_message
        self.content = ai_message.content
        self.think_start_tag = think_start_tag
        self.think_end_tag = think_end_tag
        self.reasoning_content = ai_message.additional_kwargs.get(reasoning_content_key,"")
    
    def __str__(self):
        return f"{self.think_start_tag}{self.reasoning_content}{self.think_end_tag}{self.content}"

class ReasonModelStreamResult:
    def __init__(
        self,
        message_stream: Iterator[BaseMessageChunk],
        think_start_tag="<think>",
        think_end_tag="</think>\n",
        reasoning_content_key="reasoning_content"
    ):
        self.message_stream = message_stream
        self.think_start_tag = think_start_tag
        self.think_end_tag = think_end_tag
        self.reasoning_content_key = reasoning_content_key
        self.think_stream = self.create_think_stream(message_stream)
        self.content_stream = self.create_content_stream(message_stream)
        self.new_stream = None
    def create_think_stream(self,message_stream: Iterator[BaseMessageChunk]):
        think_start_flag = False
        for message in message_stream:
            reasoning_content = message.additional_kwargs.get(
                self.reasoning_content_key,
                None
            )
            if reasoning_content is None and think_start_flag:
                return
            if reasoning_content is not None:
                if not think_start_flag:
                    think_start_flag = True
                yield reasoning_content
    def create_content_stream(self, message_stream: Iterator[BaseMessageChunk]):
        for message in message_stream:
            yield message.content
    def generate_stream(self,message_stream: Iterator[BaseMessageChunk]):
        think_start_flag = False
        for message in message_stream:
            reasoning_content = message.additional_kwargs.get(self.reasoning_content_key, None)
            if reasoning_content is not None:
                if not think_start_flag:
                    think_start_flag = True
                    yield self.think_start_tag
                yield reasoning_content
                continue
            if reasoning_content is None and think_start_flag:
                think_start_flag = False
                yield self.think_end_tag
            yield message.content
    def __iter__(self):
        if self.new_stream is not None:
            yield from self.new_stream
        else:
            yield from self.generate_stream(self.message_stream)
                

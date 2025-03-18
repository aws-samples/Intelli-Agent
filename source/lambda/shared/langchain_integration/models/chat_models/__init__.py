"""
chat models build in command pattern
"""

from shared.constant import ModelProvider
from typing import Union,Dict
from ..model_config import ModelConfig
from .. import ModelBase 

from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.messages import BaseMessage,BaseMessageChunk
from typing import Iterator,Union


class ModeMixins:
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


class ChatModelBase(ModeMixins, ModelBase):
    enable_any_tool_choice: bool = True
    enable_prefill: bool = True
    any_tool_choice_value = "any"
    default_model_kwargs: Union[Dict,None] = None
    model_map = {}

    @classmethod
    def load_module(cls,model_provider):
        _load_module(model_provider)
    
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
                "is_reasoning_model":config.is_reasoning_model
            },
        )
        return model_class


ChatModel = ChatModelBase



def _import_bedrock_models():
    from . import bedrock_models


def _import_brconnector_bedrock_models():
    from . import bedrock_models


def _import_openai_models():
    from . import openai_models


def _import_emd_models():
    from . import emd_models


def _import_sagemaker_models():
    from . import sagemaker_models


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
    ModelProvider.EMD: _import_emd_models,
    ModelProvider.SAGEMAKER: _import_sagemaker_models,
}



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


class BedrockConverseReasonModelResult:
    def __init__(self,
                 ai_message:BaseMessage,
                 think_start_tag="<think>",
                 think_end_tag="</think>",
                 reasoning_content_type="reasoning_content",
                 text_content_type="text"
        ):
        self.ai_message = ai_message
        self.think_start_tag = think_start_tag
        self.think_end_tag = think_end_tag
        self.reasoning_content_type = reasoning_content_type
        self.text_content_type = text_content_type

        self.content,self.reasoning_content = self.parese_reasoning_content(
            ai_message
        )
        
    def parese_reasoning_content(self,ai_message:BaseMessage):
        content = ai_message.content
        text_contents = []
        reasoning_contents = []
        assert isinstance(content,list),content
        for item in content:
            assert isinstance(item, dict),item
            item_type = item['type']
            if item_type == self.text_content_type:
                text_contents.append(item[self.text_content_type])
            elif item_type == self.reasoning_content_type:
                reasoning_content_type = item[self.reasoning_content_type]['type']
                if reasoning_content_type == self.text_content_type:
                    reasoning_contents.append(item[self.reasoning_content_type][self.text_content_type])
                
        return "".join(text_contents),"".join(reasoning_contents)

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




class BedrockConverseReasonModelStreamResult:
    def __init__(
        self,
        message_stream: Iterator[BaseMessageChunk],
        think_start_tag="<think>",
        think_end_tag="</think>\n",
        reasoning_content_type="reasoning_content",
        text_content_type="text"
    ):
        self.message_stream = message_stream
        self.think_start_tag = think_start_tag
        self.think_end_tag = think_end_tag
        self.reasoning_content_type = reasoning_content_type
        self.text_content_type = text_content_type
        self.think_stream = self.create_think_stream(message_stream)
        self.content_stream = self.create_content_stream(message_stream)
        self.new_stream = None
    def create_think_stream(self,message_stream: Iterator[BaseMessageChunk]):
        think_start_flag = False
        for message in message_stream:
            content_blocks:list = message.content 
            if not content_blocks:
                continue

            assert len(content_blocks) == 1, content_blocks

            content_block = content_blocks[0]
            reasoning_content = None 
            if content_block['type'] == self.reasoning_content_type:
                reasoning_content = content_block[self.reasoning_content_type][self.text_content_type]
            # reasoning_content = message.additional_kwargs.get(
            #     self.reasoning_content_key,
            #     None
            # )
            if reasoning_content is None and think_start_flag:
                return
            if reasoning_content is not None:
                if not think_start_flag:
                    think_start_flag = True
                yield reasoning_content

    def create_content_stream(self, message_stream: Iterator[BaseMessageChunk]):
        for message in message_stream:
            yield message.text()

    def generate_stream(self,message_stream: Iterator[BaseMessageChunk]):
        think_start_flag = False
        for message in message_stream:
            # reasoning_content = message.additional_kwargs.get(self.reasoning_content_key, None)
            content_blocks:list = message.content 
            if not content_blocks:
                continue

            assert len(content_blocks) == 1, content_blocks

            content_block = content_blocks[0]
            reasoning_content = None 
            if content_block['type'] == self.reasoning_content_type:
                reasoning_content = content_block[self.reasoning_content_type][self.text_content_type]

            if reasoning_content is not None:
                if not think_start_flag:
                    think_start_flag = True
                    yield self.think_start_tag
                yield reasoning_content
                continue
            if reasoning_content is None and think_start_flag:
                think_start_flag = False
                yield self.think_end_tag
            yield message.text()

    def __iter__(self):
        if self.new_stream is not None:
            yield from self.new_stream
        else:
            yield from self.generate_stream(self.message_stream)
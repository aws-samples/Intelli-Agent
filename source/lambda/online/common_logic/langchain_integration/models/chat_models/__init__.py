"""
chat models build in command pattern
"""

from common_logic.common_utils.constant import ModelProvider
from typing import Union,Dict
from ..model_config import ModelConfig
from .. import ModelBase 


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
                "default_model_kwargs": config.default_model_kwargs,
                "enable_any_tool_choice": config.enable_any_tool_choice,
                "enable_prefill": config.enable_prefill,
            },
        )
        return model_class


def _import_bedrock_models():
    from . import bedrock_models


def _import_brconnector_bedrock_models():
    from . import bedrock_models


def _import_openai_models():
    from . import openai_models


def _import_emd_models():
    from . import emd_models


def _load_module(model_provider):
    assert model_provider in MODEL_PROVIDER_LOAD_FN_MAP, (
        model_provider, MODEL_PROVIDER_LOAD_FN_MAP)
    MODEL_PROVIDER_LOAD_FN_MAP[model_provider]()


MODEL_PROVIDER_LOAD_FN_MAP = {
    ModelProvider.BEDROCK: _import_bedrock_models,
    ModelProvider.BRCONNECTOR_BEDROCK: _import_brconnector_bedrock_models,
    ModelProvider.OPENAI: _import_openai_models,
    ModelProvider.EMD: _import_emd_models

}


# MODEL_MODULE_LOAD_FN_MAP = {
#     LLMModelType.CHATGPT_35_TURBO_0125: _import_openai_models,
#     LLMModelType.CHATGPT_4_TURBO: _import_openai_models,
#     LLMModelType.CHATGPT_4O: _import_openai_models,
#     LLMModelType.CLAUDE_2: _import_bedrock_models,
#     LLMModelType.CLAUDE_INSTANCE: _import_bedrock_models,
#     LLMModelType.CLAUDE_21: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_SONNET: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_HAIKU: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_SONNET: _import_bedrock_models,
#     LLMModelType.LLAMA3_1_70B_INSTRUCT: _import_bedrock_models,
#     LLMModelType.LLAMA3_2_90B_INSTRUCT: _import_bedrock_models,
#     LLMModelType.MISTRAL_LARGE_2407: _import_bedrock_models,
#     LLMModelType.COHERE_COMMAND_R_PLUS: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_SONNET_V2: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_HAIKU: _import_bedrock_models,
#     LLMModelType.NOVA_PRO: _import_bedrock_models,
#     LLMModelType.NOVA_LITE: _import_bedrock_models,
#     LLMModelType.NOVA_MICRO: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_SONNET_US: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_OPUS_US: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_HAIKU_US: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_SONNET_V2_US: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_HAIKU_US: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_SONNET_EU: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_SONNET_EU: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_HAIKU_EU: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_SONNET_APAC: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_5_SONNET_APAC: _import_bedrock_models,
#     LLMModelType.CLAUDE_3_HAIKU_APAC: _import_bedrock_models,
#     LLMModelType.LLAMA3_1_70B_INSTRUCT_US: _import_bedrock_models,
#     LLMModelType.QWEN25_INSTRUCT_72B_AWQ: _import_emd_models,
# }

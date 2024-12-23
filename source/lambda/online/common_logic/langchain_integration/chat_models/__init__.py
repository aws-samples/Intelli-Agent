"""
chat models build in command pattern
"""
from common_logic.common_utils.constant import LLMModelType,ModelProvider
from ..model_config import MODEL_CONFIGS


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
            role = message['role']
            assert role in valid_roles, (role, valid_roles, messages)
            message['role'] = role_map[role]
            new_messages.append(message)
        return new_messages


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == "Model" or new_cls.model_id is None or name.endswith("BaseModel"):
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls


class Model(ModeMixins, metaclass=ModelMeta):
    model_id: str = None
    enable_auto_tool_choice: bool = True
    enable_prefill: bool = True
    model_map = {}
    model_provider: ModelProvider = ModelProvider.BEDROCK

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_model(cls, model_id, model_kwargs=None, **kwargs):
        # dynamic load module
        _load_module(model_id)
        return cls.model_map[model_id].create_model(model_kwargs=model_kwargs, **kwargs)

    @classmethod
    def model_id_to_class_name(cls, model_id: str) -> str:
        """Convert model ID to a valid Python class name.
        
        Examples:
            anthropic.claude-3-haiku-20240307-v1:0 -> Claude3Haiku20240307V1Model
        """
        # Remove version numbers and vendor prefixes
        name = str(model_id).split(':')[0]
        name = name.split('.')[-1]
        parts = name.replace('_', '-').split('-')

        cleaned_parts = []
        for part in parts:
            if any(c.isdigit() for c in part):
                cleaned = ''.join(c.upper() if i == 0 or part[i-1] in '- ' else c
                                  for i, c in enumerate(part))
            else:
                cleaned = part.capitalize()
            cleaned_parts.append(cleaned)

        return ''.join(cleaned_parts) + "Model"

    @classmethod
    def create_for_model(cls, model_id: str):
        """Factory method to create a model with a specific model id"""
        config = MODEL_CONFIGS[model_id]

        # Create a new class dynamically
        model_class = type(
            f"{cls.model_id_to_class_name(model_id)}",
            (cls,),
            {
                "model_id": config.model_id,
                "default_model_kwargs": config.default_model_kwargs,
                "enable_auto_tool_choice": config.enable_auto_tool_choice,
                "enable_prefill": config.enable_prefill,
            }
        )
        return model_class


def _import_bedrock_models():
    from .bedrock_models import model_classes
    # from .bedrock_models import (
    #     Claude2,
    #     ClaudeInstance,
    #     Claude21,
    #     Claude3Sonnet,
    #     Claude3Haiku,
    #     Claude35Sonnet,
    #     Claude35Haiku,
    #     Claude35SonnetV2,
    #     MistralLarge2407,
    #     Llama3d1Instruct70B,
    #     CohereCommandRPlus,
    #     NovaPro
    # )


def _import_openai_models():
    from .openai_models import (
        ChatGPT35,
        ChatGPT4Turbo,
        ChatGPT4o
    )

def _import_dmaa_models():
    from . import dmaa_models
        


def _load_module(model_id):
    assert model_id in MODEL_MODULE_LOAD_FN_MAP, (
        model_id, MODEL_MODULE_LOAD_FN_MAP)
    MODEL_MODULE_LOAD_FN_MAP[model_id]()


MODEL_MODULE_LOAD_FN_MAP = {
    LLMModelType.CHATGPT_35_TURBO_0125: _import_openai_models,
    LLMModelType.CHATGPT_4_TURBO: _import_openai_models,
    LLMModelType.CHATGPT_4O: _import_openai_models,
    LLMModelType.CLAUDE_2: _import_bedrock_models,
    LLMModelType.CLAUDE_INSTANCE: _import_bedrock_models,
    LLMModelType.CLAUDE_21: _import_bedrock_models,
    LLMModelType.CLAUDE_3_SONNET: _import_bedrock_models,
    LLMModelType.CLAUDE_3_HAIKU: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET: _import_bedrock_models,
    LLMModelType.LLAMA3_1_70B_INSTRUCT: _import_bedrock_models,
    LLMModelType.LLAMA3_2_90B_INSTRUCT: _import_bedrock_models,
    LLMModelType.MISTRAL_LARGE_2407: _import_bedrock_models,
    LLMModelType.COHERE_COMMAND_R_PLUS: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET_V2: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_HAIKU: _import_bedrock_models,
    LLMModelType.NOVA_PRO: _import_bedrock_models,
    LLMModelType.NOVA_LITE: _import_bedrock_models,
    LLMModelType.NOVA_MICRO: _import_bedrock_models,
    LLMModelType.CLAUDE_3_SONNET_US: _import_bedrock_models,
    LLMModelType.CLAUDE_3_OPUS_US: _import_bedrock_models,
    LLMModelType.CLAUDE_3_HAIKU_US: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET_V2_US: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_HAIKU_US: _import_bedrock_models,
    LLMModelType.CLAUDE_3_SONNET_EU: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET_EU: _import_bedrock_models,
    LLMModelType.CLAUDE_3_HAIKU_EU: _import_bedrock_models,
    LLMModelType.CLAUDE_3_SONNET_APAC: _import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET_APAC: _import_bedrock_models,
    LLMModelType.CLAUDE_3_HAIKU_APAC: _import_bedrock_models,
    LLMModelType.LLAMA3_1_70B_INSTRUCT_US: _import_bedrock_models,
    LLMModelType.QWEN25_INSTRUCT_72B_AWQ: _import_dmaa_models
}

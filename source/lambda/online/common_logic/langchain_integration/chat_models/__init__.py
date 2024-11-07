"""
chat models build in command pattern
"""
from common_logic.common_utils.constant import LLMModelType


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
    model_id: str = None
    enable_auto_tool_choice: bool = True
    enable_prefill: bool = True
    model_map = {}

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_model(cls, model_id, model_kwargs=None, **kwargs):
        # dynamic load module 
        _load_module(model_id)
        return cls.model_map[model_id].create_model(model_kwargs=model_kwargs, **kwargs)

def _import_bedrock_models():
    from .bedrock_models import (
        Claude2,
        ClaudeInstance,
        Claude21,
        Claude3Sonnet,
        Claude3Haiku,
        Claude35Sonnet,
        Claude35Haiku,
        Claude35SonnetV2,
        MistralLarge2407,
        Llama3d1Instruct70B,
        CohereCommandRPlus
    )

def _import_openai_models():
    from .openai_models import (
        ChatGPT35,
        ChatGPT4Turbo,
        ChatGPT4o
    )


def _load_module(model_id):
    assert model_id in MODEL_MODULE_LOAD_FN_MAP,(model_id,MODEL_MODULE_LOAD_FN_MAP)
    MODEL_MODULE_LOAD_FN_MAP[model_id]()


MODEL_MODULE_LOAD_FN_MAP = {
    LLMModelType.CHATGPT_35_TURBO_0125:_import_openai_models,
    LLMModelType.CHATGPT_4_TURBO:_import_openai_models,
    LLMModelType.CHATGPT_4O:_import_openai_models,
    LLMModelType.CLAUDE_2:_import_bedrock_models,
    LLMModelType.CLAUDE_INSTANCE:_import_bedrock_models,
    LLMModelType.CLAUDE_21:_import_bedrock_models,
    LLMModelType.CLAUDE_3_SONNET:_import_bedrock_models,
    LLMModelType.CLAUDE_3_HAIKU:_import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET:_import_bedrock_models,
    LLMModelType.LLAMA3_1_70B_INSTRUCT:_import_bedrock_models,
    LLMModelType.MISTRAL_LARGE_2407:_import_bedrock_models,
    LLMModelType.COHERE_COMMAND_R_PLUS:_import_bedrock_models,
    LLMModelType.CLAUDE_3_5_SONNET_V2:_import_bedrock_models,
    LLMModelType.CLAUDE_3_5_HAIKU:_import_bedrock_models,
}







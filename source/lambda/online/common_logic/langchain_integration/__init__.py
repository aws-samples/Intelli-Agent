# from common_logic.common_utils.constant import (
#     ModelProvider,
#     ModelTypeV2,
#     LLMModelType
# )

# class ModelMeta(type):
#     def __new__(cls, name, bases, attrs):
#         new_cls = type.__new__(cls, name, bases, attrs)
#         if (
#             name == "Model"
#             or new_cls.model_id is None
#             or name.endswith("BaseModel")
#             or name.lower().endswith("basemodel")
#         ):
#             return new_cls
#         new_cls.model_map[new_cls.get_model_id()] = new_cls
#         return new_cls


# class Model(metaclass=ModelMeta):
#     model_id: LLMModelType
#     model_type: ModelTypeV2
#     model_provider: ModelProvider

#     @classmethod
#     def create_model(cls, model_kwargs=None, **kwargs):
#         raise NotImplementedError

#     @classmethod
#     def load_module(cls,model_type:str,model_provider:str):
#         if model_type == ModelTypeV2.LLM:
#             pass 



#     @classmethod
#     def get_model_id(cls,model_id=None,model_provider=None):
#         if model_id is None:
#             model_id = cls.model_id
#         if model_provider is None:
#             model_provider = cls.model_provider
#         return f"{model_id}__{model_provider}"
#     @classmethod
#     def get_model(cls, model_id, model_kwargs=None, **kwargs):
#         model_provider = kwargs['provider']
#         # dynamic load module
#         _load_module(model_provider)
#         model_identify = cls.get_model_id(model_id=model_id,model_provider=model_provider)
#         return cls.model_map[model_identify].create_model(model_kwargs=model_kwargs, **kwargs)

#     @classmethod
#     def model_id_to_class_name(cls, model_id: str) -> str:
#         """Convert model ID to a valid Python class name.

#         Examples:
#             anthropic.claude-3-haiku-20240307-v1:0 -> Claude3Haiku20240307V1Model
#         """
#         # Remove version numbers and vendor prefixes
#         name = str(model_id).split(":")[0]
#         name = name.split(".")[-1]
#         parts = name.replace("_", "-").split("-")

#         cleaned_parts = []
#         for part in parts:
#             if any(c.isdigit() for c in part):
#                 cleaned = "".join(c.upper() if i == 0 or part[i - 1] in "- " else c for i, c in enumerate(part))
#             else:
#                 cleaned = part.capitalize()
#             cleaned_parts.append(cleaned)

#         return "".join(cleaned_parts) + "Model"

#     @classmethod
#     def create_for_model(cls, config: ModelConfig):
#         """Factory method to create a model with a specific model id"""
#         # config = MODEL_CONFIGS[model_id]
#         model_id = config.model_id
#         # Create a new class dynamically
#         model_class = type(
#             f"{cls.model_id_to_class_name(model_id)}",
#             (cls,),
#             {
#                 "model_id": model_id,
#                 "default_model_kwargs": config.default_model_kwargs,
#                 "enable_any_tool_choice": config.enable_any_tool_choice,
#                 "enable_prefill": config.enable_prefill,
#             },
#         )
#         return model_class

#     @classmethod
#     def create_for_models(cls, configs: list[ModelConfig]):
#         for config in configs:
#             cls.create_for_model(config)
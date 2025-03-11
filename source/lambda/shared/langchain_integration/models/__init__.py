from ...constant import ModelProvider

class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if (
            name == "Model"
            # or new_cls.model_id is None
            or name.endswith(("ModelBase","BaseModel","ModelCreator"))
            or name.lower().endswith("basemodel")
        ):
            return new_cls
        new_cls.model_map[new_cls.get_model_id()] = new_cls
        return new_cls
    

class ModelBase(metaclass=ModelMeta):
    model_id: str
    model_provider: ModelProvider

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

    def load_module(cls,model_provider):
        raise NotImplementedError
    
    @classmethod
    def get_model(cls, model_id, model_kwargs=None, **kwargs):
        model_provider = kwargs['provider']
        # dynamic load module
        cls.load_module(model_provider)
        model_identify = cls.get_model_id(
            model_id=model_id, model_provider=model_provider)
        return cls.model_map[model_identify].create_model(model_kwargs=model_kwargs, **kwargs)

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
                    c.upper() if i == 0 or part[i - 1] in "- " else c for i, c in enumerate(part))
            else:
                cleaned = part.capitalize()
            cleaned_parts.append(cleaned)

        return "".join(cleaned_parts) + "Model"

    @classmethod
    def create_for_model(cls, config):
        """Factory method to create a model with a specific model id"""
        raise NotImplementedError

    @classmethod
    def create_for_models(cls, configs):
        for config in configs:
            cls.create_for_model(config)



from .chat_models import ChatModel
from .embedding_models import EmbeddingModel
from .rerank_models import RerankModel

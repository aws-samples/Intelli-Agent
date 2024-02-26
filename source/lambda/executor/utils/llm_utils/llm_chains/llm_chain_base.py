
class LLMChainMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == 'LLMChain':
            return new_cls
        new_cls.model_map[new_cls.get_chain_id()] = new_cls
        return new_cls
    
class LLMChain(metaclass=LLMChainMeta):
    model_map = {}
    @classmethod
    def get_chain_id(cls):
        return cls._get_chain_id(cls.model_id,cls.intent_type)
    
    @staticmethod
    def _get_chain_id(model_id,intent_type):
        return f"{model_id}__{intent_type}"

    @classmethod
    def get_chain(cls,model_id,intent_type,model_kwargs=None, **kwargs):
        return cls.model_map[cls._get_chain_id(model_id,intent_type)].create_chain(
            model_kwargs=model_kwargs, **kwargs
        )
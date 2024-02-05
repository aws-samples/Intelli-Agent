from .llm_chains import LLMChain
from .llm_models import Model

def get_llm_chain(model_id, intent_type, model_kwargs=None, **kwargs):
    return LLMChain.get_chain(
        model_id,
        intent_type,
        model_kwargs=model_kwargs,
        **kwargs
    )

def get_llm_model(model_id,model_kwargs=None):
    return Model.get_model(model_id,model_kwargs=model_kwargs)

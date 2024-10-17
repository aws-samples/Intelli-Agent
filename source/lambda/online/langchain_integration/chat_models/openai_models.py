from langchain_openai import ChatOpenAI
from common_logic.common_utils.constant import LLMModelType
from common_logic.common_utils.logger_utils import get_logger
from . import Model

logger = get_logger("openai_model")

class ChatGPT35(Model):
    model_id = LLMModelType.CHATGPT_35_TURBO_0125
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.7, "top_p": 0.9}

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        llm = ChatOpenAI(
            model=cls.model_id,
            **model_kwargs,
        )
        return llm


class ChatGPT4Turbo(ChatGPT35):
    model_id = LLMModelType.CHATGPT_4_TURBO


class ChatGPT4o(ChatGPT35):
    model_id = LLMModelType.CHATGPT_4O
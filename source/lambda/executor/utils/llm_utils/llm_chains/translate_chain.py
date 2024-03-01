# translate chain
from langchain.schema.runnable import RunnableLambda
from ...constant import QUERY_TRANSLATE_TYPE

from .chat_chain import Iternlm2Chat7BChatChain
class Iternlm2Chat7BTranslateChain(Iternlm2Chat7BChatChain):
    intent_type = QUERY_TRANSLATE_TYPE
    default_model_kwargs = {
        "temperature": 0.0,
        "max_new_tokens": 200
    }

    @classmethod
    def create_prompt(cls,x):
        query = x['query']
        target_lang = x['target_lang']
        history = cls.create_history(x)
        meta_instruction = f'你是一个有经验的翻译助理, 正在将用户的问题翻译成{target_lang}，请不要试图去回答用户的问题，仅仅做翻译。'
        query = f'请将文本:\n "{query}" \n 翻译成{target_lang}。\n 请直接翻译文本，不要输出多余的文本。'
        
        prompt = cls.build_prompt(
            query=query,
            history=history,
            meta_instruction=meta_instruction
        )
        return prompt

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        llm_chain = super().create_chain(model_kwargs=model_kwargs,**kwargs)
        llm_chain = llm_chain | RunnableLambda(lambda x:x.strip('"'))  # postprocess
        return llm_chain 


class Iternlm2Chat20BTranslateChain(Iternlm2Chat7BTranslateChain):
    model_id = "internlm2-chat-20b"
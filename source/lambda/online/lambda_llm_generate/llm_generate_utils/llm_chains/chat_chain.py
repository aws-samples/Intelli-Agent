# chat llm chains

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain_core.messages import AIMessage,SystemMessage
from langchain.prompts import ChatPromptTemplate,HumanMessagePromptTemplate
from langchain_core.messages import convert_to_messages


from ..llm_models import Model
from .llm_chain_base import LLMChain

from common_logic.common_utils.constant import (
    MessageType,
    LLMTaskType,
    LLMModelType,
)
from common_logic.common_utils.time_utils import get_china_now
from common_logic.common_utils.prompt_utils import get_prompt_template

AI_MESSAGE_TYPE = MessageType.AI_MESSAGE_TYPE
HUMAN_MESSAGE_TYPE = MessageType.HUMAN_MESSAGE_TYPE
QUERY_TRANSLATE_TYPE = LLMTaskType.QUERY_TRANSLATE_TYPE
SYSTEM_MESSAGE_TYPE = MessageType.SYSTEM_MESSAGE_TYPE


class Claude2ChatChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.CHAT

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        system_prompt_template = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="main"     
        ).prompt_template

        system_prompt = kwargs.get('system_prompt',system_prompt_template)
        prefill =  kwargs.get('prefill',None)
        messages = [
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}")
        ]
        if system_prompt:
            messages.insert(0,SystemMessage(content=system_prompt))
        
        if prefill is not None:
            messages.append(AIMessage(content=prefill))

        messages_template = ChatPromptTemplate.from_messages(messages)
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = messages_template | RunnableLambda(lambda x: x.messages)
        if stream:
            chain = (
                chain | RunnableLambda(lambda messages: llm.stream(messages))
                | RunnableLambda(lambda x: (i.content for i in x))
            )
        else:
            chain = chain | llm | RunnableLambda(lambda x: x.content)

        return chain


class Claude21ChatChain(Claude2ChatChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceChatChain(Claude2ChatChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetChatChain(Claude2ChatChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuChatChain(Claude2ChatChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35SonnetChatChain(Claude2ChatChain):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"


class Mixtral8x7bChatChain(Claude2ChatChain):
    model_id = LLMModelType.MIXTRAL_8X7B_INSTRUCT
    default_model_kwargs = {"max_tokens": 4096, "temperature": 0.01}


class Baichuan2Chat13B4BitsChatChain(LLMChain):
    model_id = LLMModelType.BAICHUAN2_13B_CHAT
    intent_type = LLMTaskType.CHAT
    default_model_kwargs = {
        "max_new_tokens": 2048,
        "temperature": 0.3,
        "top_k": 5,
        "top_p": 0.85,
        # "repetition_penalty": 1.05,
        "do_sample": True,
    }

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        # chat_history = kwargs.pop('chat_history',[])
        model_kwargs = model_kwargs or {}
        model_kwargs.update({"stream": stream})
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        llm_chain = RunnableLambda(lambda x: llm.invoke(x, stream=stream))
        return llm_chain


class Iternlm2Chat7BChatChain(LLMChain):
    model_id = LLMModelType.INTERNLM2_CHAT_7B
    intent_type = LLMTaskType.CHAT

    default_model_kwargs = {"temperature": 0.5, "max_new_tokens": 1000}

    @staticmethod
    def build_prompt(
        query: str,
        history=[],
        meta_instruction="You are an AI assistant whose name is InternLM (书生·浦语).\n"
        "- InternLM (书生·浦语) is a conversational language model that is developed by Shanghai AI Laboratory (上海人工智能实验室). It is designed to be helpful, honest, and harmless.\n"
        "- InternLM (书生·浦语) can understand and communicate fluently in the language chosen by the user such as English and 中文.",
    ):
        prompt = ""
        if meta_instruction:
            prompt += f"""<|im_start|>system\n{meta_instruction}<|im_end|>\n"""
        for record in history:
            prompt += f"""<|im_start|>user\n{record[0]}<|im_end|>\n<|im_start|>assistant\n{record[1]}<|im_end|>\n"""
        prompt += f"""<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"""
        return prompt

    @classmethod
    def create_history(cls, x):
        chat_history = x.get("chat_history", [])
        chat_history = convert_to_messages(chat_history)

        assert len(chat_history) % 2 == 0, chat_history
        history = []
        for i in range(0, len(chat_history), 2):
            user_message = chat_history[i]
            ai_message = chat_history[i + 1]
            assert (
                user_message.type == HUMAN_MESSAGE_TYPE
                and ai_message.type == AI_MESSAGE_TYPE
            ), chat_history
            history.append((user_message.content, ai_message.content))
        return history

    @classmethod
    def create_prompt(cls, x,system_prompt=None):
        history = cls.create_history(x)
        if system_prompt is None:
            system_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="main"     
        ).prompt_template

        prompt = cls.build_prompt(
            query=x["query"],
            history=history,
            meta_instruction=system_prompt,
        )
        return prompt

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        stream = kwargs.get("stream", False)
        system_prompt = kwargs.get("system_prompt",None)
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)

        prompt_template = RunnablePassthrough.assign(
            prompt=RunnableLambda(lambda x: cls.create_prompt(x,system_prompt=system_prompt))
        )
        llm_chain = prompt_template | RunnableLambda(
            lambda x: llm.invoke(x, stream=stream)
        )
        return llm_chain


class Iternlm2Chat20BChatChain(Iternlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_20B


class GLM4Chat9BChatChain(LLMChain):
    model_id = LLMModelType.GLM_4_9B_CHAT
    intent_type = LLMTaskType.CHAT
    default_model_kwargs = {
        "max_new_tokens": 1024,
        "timeout": 60,
        "temperature": 0.1,
    }
    @classmethod
    def create_chat_history(cls,x, system_prompt=None):
        if system_prompt is None:
            system_prompt = get_prompt_template(
                model_id=cls.model_id,
                task_type=cls.intent_type,
                prompt_name="main"     
            ).prompt_template

        chat_history = x['chat_history']

        if system_prompt is not None:
            chat_history = [{"role":"system","content": system_prompt}] + chat_history
        chat_history = chat_history + [{"role":MessageType.HUMAN_MESSAGE_TYPE,"content":x['query']}]

        return chat_history
     
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        system_prompt = kwargs.get("system_prompt",None)
        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )

        chain = RunnablePassthrough.assign(
            chat_history = RunnableLambda(lambda x: cls.create_chat_history(x,system_prompt=system_prompt)) 
        ) | RunnableLambda(lambda x: llm.invoke(x))
        
        return chain


class Qwen2Instruct7BChatChain(LLMChain):
    model_id = LLMModelType.QWEN2INSTRUCT7B
    intent_type = LLMTaskType.CHAT

    @classmethod
    def create_chat_history(cls,x, system_prompt=None):
        if system_prompt is None:
            system_prompt = get_prompt_template(
                model_id=cls.model_id,
                task_type=cls.intent_type,
                prompt_name="main"     
            ).prompt_template

        chat_history = x['chat_history']

        if system_prompt is not None:
            chat_history = [{"role":"system", "content": system_prompt}] + chat_history
        
        _chat_history = chat_history + [{"role": MessageType.HUMAN_MESSAGE_TYPE, "content":x['query']}]
        chat_history = []
        for message in _chat_history:
            assert MessageType.has_value(message['role']), message
            if message['role'] == MessageType.HUMAN_MESSAGE_TYPE:
                role  = 'user'
            elif message['role'] == MessageType.AI_MESSAGE_TYPE:
                role = 'assistant'
            else:
                role = "system"
            chat_history.append({"role":role,"content":message['content']})
        return chat_history


    @classmethod
    def parse_function_calls_from_ai_message(cls,message:dict):
        return message['text']
            

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        system_prompt = kwargs.get("system_prompt",None)

        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )

        chain = RunnablePassthrough.assign(
            chat_history = RunnableLambda(lambda x: cls.create_chat_history(x,system_prompt=system_prompt)) 
        ) | RunnableLambda(lambda x: llm.invoke(x)) | RunnableLambda(lambda x: cls.parse_function_calls_from_ai_message(x))
        
        return chain

class Qwen2Instruct72BChatChain(Qwen2Instruct7BChatChain):
    model_id = LLMModelType.QWEN2INSTRUCT72B


    
class ChatGPT35ChatChain(LLMChain):
    model_id = LLMModelType.CHATGPT_35_TURBO
    intent_type = LLMTaskType.CHAT

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        system_prompt = kwargs.get('system_prompt',None)
        prefill =  kwargs.get('prefill',None)
        messages = [
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}")
        ]
        if system_prompt is not None:
            messages.insert(SystemMessage(content=system_prompt),0)
        
        if prefill is not None:
            messages.append(AIMessage(content=prefill))

        messages_template = ChatPromptTemplate.from_messages(messages)
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = messages_template | RunnableLambda(lambda x: x.messages)
        if stream:
            chain = (
                chain | RunnableLambda(lambda messages: llm.stream(messages))
                | RunnableLambda(lambda x: (i.content for i in x))
            )
        else:
            chain = chain | llm | RunnableLambda(lambda x: x.content)

        return chain

class ChatGPT4ChatChain(ChatGPT35ChatChain):
    model_id = LLMModelType.CHATGPT_4_TURBO

class ChatGPT4oChatChain(ChatGPT35ChatChain):
    model_id = LLMModelType.CHATGPT_4O

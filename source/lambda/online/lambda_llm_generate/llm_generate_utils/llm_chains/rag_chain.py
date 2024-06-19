# rag llm chains


from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from common_utils.constant import (
    LLMTaskType
)

# from ...prompt_template import convert_chat_history_from_fstring_format
from ..llm_models import Model
from .llm_chain_base import LLMChain

# TODO: pass prompt template to the chain
BEDROCK_RAG_CHAT_SYSTEM_PROMPT = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

Here are some documents for you to reference for your query.
<docs>
{context}
</docs>"""

def get_claude_rag_context(contexts: list):
    assert isinstance(contexts, list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i, context in enumerate(contexts):
        context_xml = context_template.format(index=i + 1, content=context)
        context_xmls.append(context_xml)

    context = "\n".join(context_xmls)
    return context


class Claude2RagLLMChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)

        # history
        chat_history = kwargs.get("chat_history", [])
        chat_messages = [
            SystemMessagePromptTemplate.from_template(BEDROCK_RAG_CHAT_SYSTEM_PROMPT)
        ]
        chat_messages = chat_messages + chat_history
        chat_messages += [HumanMessagePromptTemplate.from_template("{query}")]
        context_chain = RunnablePassthrough.assign(
            context=RunnableLambda(lambda x: get_claude_rag_context(x["contexts"]))
        )
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
        if stream:
            chain = (
                chain
                | RunnableLambda(lambda x: llm.stream(x.messages))
                | RunnableLambda(lambda x: (i.content for i in x))
            )
        else:
            chain = chain | llm | RunnableLambda(lambda x: x.content)
        return chain


class Claude21RagLLMChain(Claude2RagLLMChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceRAGLLMChain(Claude2RagLLMChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetRAGLLMChain(Claude2RagLLMChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuRAGLLMChain(Claude2RagLLMChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


class Mixtral8x7bChatChain(Claude2RagLLMChain):
    model_id = "mistral.mixtral-8x7b-instruct-v0:1"


from .chat_chain import GLM4Chat9BChatChain

class GLM4Chat9BRagChain(GLM4Chat9BChatChain):
    model_id = "glm-4-9b-chat"
    intent_type = LLMTaskType.RAG


from .chat_chain import Baichuan2Chat13B4BitsChatChain



class Baichuan2Chat13B4BitsKnowledgeQaChain(Baichuan2Chat13B4BitsChatChain):
    model_id = "Baichuan2-13B-Chat-4bits"
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        llm_chain = super().create_chain(model_kwargs=model_kwargs, **kwargs)

        def add_system_prompt(x):
            context = "\n".join(x["contexts"])
            _chat_history = x["chat_history"] + [
                ("system", f"给定下面的背景知识:\n{context}\n回答下面的问题:\n")
            ]
            return _chat_history

        chat_history_chain = RunnablePassthrough.assign(
            chat_history=RunnableLambda(lambda x: add_system_prompt(x))
        )
        llm_chain = chat_history_chain | llm_chain
        return llm_chain


from .chat_chain import Iternlm2Chat7BChatChain


class Iternlm2Chat7BKnowledgeQaChain(Iternlm2Chat7BChatChain):
    mdoel_id = "internlm2-chat-7b"
    intent_type = LLMTaskType.RAG
    default_model_kwargs = {"temperature": 0.05, "max_new_tokens": 1000}

    @classmethod
    def create_prompt(cls, x):
        query = x["query"]
        contexts = x["contexts"]
        history = cls.create_history(x)
        context = "\n".join(contexts)
        meta_instruction = f"你是一个Amazon AWS的客服助理小Q，帮助的用户回答使用AWS过程中的各种问题。\n面对用户的问题，你需要给出中文回答，注意不要在回答中重复输出内容。\n下面给出相关问题的背景知识, 需要注意的是如果你认为当前的问题不能在背景知识中找到答案, 你需要拒答。\n背景知识:\n{context}\n\n"
        # meta_instruction = f"You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use simplified Chinese to response the qustion. I’m going to tip $300K for a better answer! "
        # meta_instruction = f'You are an expert AI on a question and answer task. \nUse the "Following Context" when answering the question. If you don't know the answer, reply to the "Following Text" in the header and answer to the best of your knowledge, or if you do know the answer, answer without the "Following Text"'
        #         meta_instruction = """You are an expert AI on a question and answer task.
        # Use the "Following Context" when answering the question. If you don't know the answer, reply to the "Following Text" in the header and answer to the best of your knowledge, or if you do know the answer, answer without the "Following Text". If a question is asked in Korean, translate it to English and always answer in Korean.
        # Following Text: "I didn't find the answer in the context given, but here's what I know! **I could be wrong, so cross-verification is a must!**"""
        #         meta_instruction = """You are an expert AI on a question and answer task.
        # Use the "Following Context" when answering the question. If you don't know the answer, reply to the "Sorry, I don't know". """
        # query = f"Question: {query}\nContext:\n{context}"
        #         query = f"""Following Context: {context}
        # Question: {query}"""
        query = f"问题: {query}"
        prompt = cls.build_prompt(
            query=query, history=history, meta_instruction=meta_instruction
        )
        # prompt = prompt + "回答: 让我先来判断一下问题的答案是否包含在背景知识中。"
        prompt = prompt + f"回答: 经过慎重且深入的思考, 根据背景知识, 我的回答如下:\n"
        print("internlm2 prompt: \n", prompt)
        return prompt


class Iternlm2Chat20BKnowledgeQaChain(Iternlm2Chat7BKnowledgeQaChain):
    model_id = "internlm2-chat-20b"

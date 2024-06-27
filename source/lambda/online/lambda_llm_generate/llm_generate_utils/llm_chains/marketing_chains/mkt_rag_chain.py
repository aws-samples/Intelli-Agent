from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType
)
from ..chat_chain import Iternlm2Chat7BChatChain
from common_logic.common_utils.prompt_utils import register_prompt_templates,get_prompt_template

INTERLM2_RAG_PROMPT_TEMPLATE = "你是一个Amazon AWS的客服助理小Q，帮助的用户回答使用AWS过程中的各种问题。\n面对用户的问题，你需要给出中文回答，注意不要在回答中重复输出内容。\n下面给出相关问题的背景知识, 需要注意的是如果你认为当前的问题不能在背景知识中找到答案, 你需要拒答。\n背景知识:\n{context}\n\n"

register_prompt_templates(
    model_ids=[LLMModelType.INTERNLM2_CHAT_7B,LLMModelType.INTERNLM2_CHAT_20B],
    task_type=LLMTaskType.RAG,
    prompt_template=INTERLM2_RAG_PROMPT_TEMPLATE,
    prompt_name="main"
)

class Iternlm2Chat7BKnowledgeQaChain(Iternlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_7B
    intent_type = LLMTaskType.RAG
    default_model_kwargs = {"temperature": 0.05, "max_new_tokens": 1000}

    @classmethod
    def create_prompt(cls, x):
        query = x["query"]
        contexts = x["contexts"]
        history = cls.create_history(x)
        context = "\n".join(contexts)
        prompt_template = get_prompt_template(
            model_id = cls.model_id,
            task_type = cls.task_type,
            prompt_name = "main"
        ).prompt_template
        meta_instruction = prompt_template.format(context)
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
    model_id = LLMModelType.INTERNLM2_CHAT_20B
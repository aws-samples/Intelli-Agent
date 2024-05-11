from langchain.prompts import (
    ChatMessagePromptTemplate,
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)
from langchain.schema.runnable import RunnableLambda

from layer_logic.utils.constant import LLMTaskType
from ..llm_chains.chat_chain import Iternlm2Chat7BChatChain
from ..llm_chains.llm_chain_base import LLMChain
from ..llm_models import Model

STEPBACK_PROMPTING_TYPE = LLMTaskType.STEPBACK_PROMPTING_TYPE

class Iternlm2Chat7BStepBackChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = STEPBACK_PROMPTING_TYPE

    default_model_kwargs = {"temperature": 0.1, "max_new_tokens": 200}

    @classmethod
    def create_prompt(cls, x):
        meta_instruction_template = "You are an expert at world knowledge. Your task is to step back and paraphrase a question to a more generic step-back question, which is easier to answer. Here are a few examples: {few_examples}"
        # meta_instruction_template = "你是一个拥有世界知识的专家. 你的任务是将问题转述为更通用的问题，这样更容易回答。更通用指的是将问题进行抽象表达，省略问题中的各种细节，包括具体时间，地点等。 下面有一些例子: {few_examples}"

        few_examples = [
            {
                "input": "阿尔伯特-爱因斯坦的出生地是哪里？",
                "output": "阿尔伯特-爱因斯坦的个人经历是怎样的？",
            },
            {
                "input": "特斯拉在中国上海有多少门店",
                "output": "特斯拉在中国的门店分布情况",
            },
        ]

        few_examples_template = """origin question: {origin_question}
        step-back question: {step_back_question}
        """
        few_examples_strs = []
        for few_example in few_examples:
            few_examples_strs.append(
                few_examples_template.format(
                    origin_question=few_example["input"],
                    step_back_question=few_example["output"],
                )
            )
        meta_instruction = meta_instruction_template.format(
            few_examples="\n\n".join(few_examples_strs)
        )
        prompt = (
            cls.build_prompt(
                query=f"origin question: {x['query']}",
                history=[],
                meta_instruction=meta_instruction,
            )
            + "step-back question: "
        )
        return prompt


class Iternlm2Chat20BStepBackChain(Iternlm2Chat7BStepBackChain):
    model_id = "internlm2-chat-20b"
    intent_type = STEPBACK_PROMPTING_TYPE


class Claude2StepBackChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = STEPBACK_PROMPTING_TYPE

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        examples = [
            {
                "input": "Could the members of The Police perform lawful arrests?",
                "output": "what can the members of The Police do?",
            },
            {
                "input": "Jan Sindel’s was born in what country?",
                "output": "what is Jan Sindel’s personal history?",
            },
        ]
        # We now transform these to example messages
        example_prompt = ChatPromptTemplate.from_messages(
            [
                ("human", "{input}"),
                ("ai", "{output}"),
            ]
        )
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at world knowledge. Your task is to step back and paraphrase a question to a more generic step-back question, which is easier to answer. Here are a few examples:""",
                ),
                # Few shot examples
                few_shot_prompt,
                # New question
                ("user", "{query}"),
            ]
        )

        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = prompt | llm
        if stream:
            chain = (
                prompt
                | RunnableLambda(lambda x: llm.stream(x.messages))
                | RunnableLambda(lambda x: (i.content for i in x))
            )

        else:
            chain = prompt | llm | RunnableLambda(lambda x: x.content)
        return chain


class Claude21StepBackChain(Claude2StepBackChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceStepBackChain(Claude2StepBackChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetStepBackChain(Claude2StepBackChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuStepBackChain(Claude2StepBackChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

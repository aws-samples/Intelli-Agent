# conversation summary chain
from typing import List
import json
from langchain.schema.runnable import (
    RunnableLambda
)


from ..models import ChatModel 
# from .chat_chain import Internlm2Chat7BChatChain
from . import LLMChain
from shared.constant import (
    MessageType,
    LLMTaskType,
    LLMModelType
)

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    convert_to_messages
)
from langchain.prompts import (
    HumanMessagePromptTemplate,
    ChatPromptTemplate
)
from ..models.model_config import (
    BEDROCK_MODEL_CONFIGS,
    OPENAI_MODEL_CONFIGS,
    QWEN25_MODEL_CONFIGS,
    SILICONFLOW_DEEPSEEK_MODEL_CONFIGS
)
from ...utils.prompt_utils import get_prompt_template
from ...utils.logger_utils import get_logger, print_llm_messages

logger = get_logger("conversation_summary")

AI_MESSAGE_TYPE = MessageType.AI_MESSAGE_TYPE
HUMAN_MESSAGE_TYPE = MessageType.HUMAN_MESSAGE_TYPE
QUERY_TRANSLATE_TYPE = LLMTaskType.QUERY_TRANSLATE_TYPE
SYSTEM_MESSAGE_TYPE = MessageType.SYSTEM_MESSAGE_TYPE


class ConversationSummaryBaseChain(LLMChain):
    
    intent_type = LLMTaskType.CONVERSATION_SUMMARY_TYPE

    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.1, "top_p": 0.9}
    prefill = "From PersonU's point of view, here is the single standalone sentence:"

    @staticmethod
    def create_conversational_context(chat_history: List[BaseMessage]):
        conversational_contexts = []
        for his in chat_history:
            assert isinstance(his, (AIMessage, HumanMessage)), his
            content = his.content
            if isinstance(his, HumanMessage):
                conversational_contexts.append(f"USER: {content}")
            else:
                conversational_contexts.append(f"AI: {content}")
        conversational_context = "\n".join(conversational_contexts)
        return conversational_context

    @classmethod
    def format_conversation(cls, conversation: list[BaseMessage]):
        conversation_strs = []
        for message in conversation:
            assert isinstance(message, (AIMessage, HumanMessage)), message
            content = message.content
            if isinstance(message, HumanMessage):
                conversation_strs.append(f"PersonU: {content}")
            elif isinstance(message, AIMessage):
                conversation_strs.append(f"PersonA: {content}")
        return "\n".join(conversation_strs)

    @classmethod
    def create_messages_inputs(cls, x: dict, user_prompt, few_shots: list[dict]):
        # create few_shots
        few_shot_messages = []
        for few_shot in few_shots:
            conversation = cls.format_conversation(
                convert_to_messages(few_shot['conversation'])
            )
            few_shot_messages.append(HumanMessage(content=user_prompt.format(
                conversation=conversation,
                current_query=few_shot['conversation'][-1]['content']
            )))
            few_shot_messages.append(
                AIMessage(content=f"{cls.prefill} {few_shot['rewrite_query']}"))

        # create current cocnversation
        cur_messages = convert_to_messages(
            x['chat_history'] +
            [{"role": MessageType.HUMAN_MESSAGE_TYPE, "content": x['query']}]
        )

        conversation = cls.format_conversation(cur_messages)
        return {
            "conversation": conversation,
            "few_shots": few_shot_messages,
            "current_query": x['query']
        }

    @classmethod
    def create_messages_chain(cls, **kwargs):
        enable_prefill = kwargs['enable_prefill']
        system_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="system_prompt"
        ).prompt_template

        user_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="user_prompt"
        ).prompt_template

        few_shots = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="few_shots"
        ).prompt_template

        system_prompt = kwargs.get("system_prompt", system_prompt)
        user_prompt = kwargs.get('user_prompt', user_prompt)

        messages = [
            SystemMessage(content=system_prompt),
            ('placeholder', '{few_shots}'),
            HumanMessagePromptTemplate.from_template(user_prompt)
        ]
        if enable_prefill:
            messages.append(AIMessage(content=cls.prefill))
        else:
            messages.append(HumanMessage(content=cls.prefill))

        cqr_template = ChatPromptTemplate.from_messages(messages)
        return RunnableLambda(lambda x: cls.create_messages_inputs(x, user_prompt=user_prompt, few_shots=json.loads(few_shots))) | cqr_template

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        llm = ChatModel.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )
        messages_chain = cls.create_messages_chain(
            **kwargs, enable_prefill=llm.enable_prefill)
        chain = messages_chain | RunnableLambda(lambda x: print_llm_messages(f"conversation summary messages: {x.messages}") or x.messages) \
            | llm | RunnableLambda(lambda x: x.text().replace(cls.prefill, "").strip())
        return chain


ConversationSummaryBaseChain.create_for_chains(BEDROCK_MODEL_CONFIGS, LLMTaskType.CONVERSATION_SUMMARY_TYPE)
ConversationSummaryBaseChain.create_for_chains(OPENAI_MODEL_CONFIGS, LLMTaskType.CONVERSATION_SUMMARY_TYPE)
ConversationSummaryBaseChain.create_for_chains(QWEN25_MODEL_CONFIGS, LLMTaskType.CONVERSATION_SUMMARY_TYPE)
ConversationSummaryBaseChain.create_for_chains(SILICONFLOW_DEEPSEEK_MODEL_CONFIGS, LLMTaskType.CONVERSATION_SUMMARY_TYPE)


# class Internlm2Chat20BConversationSummaryChain(Internlm2Chat7BChatChain):
#     model_id = LLMModelType.INTERNLM2_CHAT_20B
#     default_model_kwargs = {
#         "max_new_tokens": 300,
#         "temperature": 0.1,
#         "stop_tokens": ["\n\n"],
#     }

#     @classmethod
#     def create_prompt(cls, x, system_prompt=None):
#         chat_history = x["chat_history"]
#         conversational_contexts = []
#         for his in chat_history:
#             role = his['role']
#             assert role in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
#             if role == HUMAN_MESSAGE_TYPE:
#                 conversational_contexts.append(f"USER: {his['content']}")
#             else:
#                 conversational_contexts.append(f"AI: {his['content']}")
#         if system_prompt is None:
#             system_prompt = get_prompt_template(
#                 model_id=cls.model_id,
#                 task_type=cls.intent_type,
#                 prompt_name="system_prompt"
#             ).prompt_template

#         conversational_context = "\n".join(conversational_contexts)
#         prompt = cls.build_prompt(
#             system_prompt.format(
#                 history=conversational_context, question=x["query"]
#             )
#         )
#         prompt = prompt + "Standalone Question: "
#         return prompt


# class Internlm2Chat7BConversationSummaryChain(Internlm2Chat20BConversationSummaryChain):
#     model_id = LLMModelType.INTERNLM2_CHAT_7B


# class Qwen2Instruct72BConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.QWEN25_INSTRUCT_72B_AWQ


# class Qwen2Instruct72BConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.QWEN15INSTRUCT32B


# class Qwen2Instruct7BConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.QWEN2INSTRUCT7B


# class GLM4Chat9BConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.GLM_4_9B_CHAT



# class ChatGPT35ConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.GPT3D5TURBO0125


# class ChatGPT4TurboConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.GPT4TURBO20240409


# class ChatGPT4oConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.GPT4O20240806


# class ChatGPT4oMiniConversationSummaryChain(ConversationSummaryBaseChain):
#     model_id = LLMModelType.GPT4OMINI20240718


# chain_classes = {
#     f"{LLMChain.model_id_to_class_name(model_id, LLMTaskType.CONVERSATION_SUMMARY_TYPE)}": ConversationSummaryBaseChain.create_for_model(model_id, LLMTaskType.CONVERSATION_SUMMARY_TYPE)
#     for model_id in MODEL_CONFIGS
# }

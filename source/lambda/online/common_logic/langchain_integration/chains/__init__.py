from typing import Any
from common_logic.common_utils.constant import LLMTaskType
from ..model_config import MODEL_CONFIGS


class LLMChainMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == "LLMChain":
            return new_cls
        new_cls.model_map[new_cls.get_chain_id()] = new_cls
        return new_cls


class LLMChain(metaclass=LLMChainMeta):
    model_map = {}

    @classmethod
    def get_chain_id(cls):
        return cls._get_chain_id(cls.model_id, cls.intent_type)

    @staticmethod
    def _get_chain_id(model_id, intent_type):
        return f"{model_id}__{intent_type}"

    @classmethod
    def get_chain(cls, model_id, intent_type, model_kwargs=None, **kwargs):
        # dynamic import
        _load_module(intent_type)
        return cls.model_map[cls._get_chain_id(model_id, intent_type)].create_chain(
            model_kwargs=model_kwargs, **kwargs
        )

    @classmethod
    def model_id_to_class_name(cls, model_id: str, intent_type: str) -> str:
        """Convert model ID to a valid Python class name.
        
        Examples:
            anthropic.claude-3-haiku-20240307-v1:0 -> Claude3Haiku20240307V1{IntentType}Chain
        """
        # Remove version numbers and vendor prefixes
        name = str(model_id).split(':')[0]
        name = name.split('.')[-1]

        # Split by hyphens and clean each part
        parts = name.replace('_', '-').split('-')

        cleaned_parts = []
        for part in parts:
            # Handle parts with numbers
            if any(c.isdigit() for c in part):
                # Keep numbers but capitalize letters
                cleaned = ''.join(c.upper() if i == 0 or part[i-1] in '- ' else c
                                  for i, c in enumerate(part))
            else:
                cleaned = part.capitalize()
            cleaned_parts.append(cleaned)

        return ''.join(cleaned_parts) + intent_type.capitalize() + "Chain"

    @classmethod
    def create_for_model(cls, model_id: str, intent_type: str):
        """Factory method to create a chain for a specific model"""
        config = MODEL_CONFIGS[model_id]

        # Create a new class dynamically
        chain_class = type(
            f"{cls.model_id_to_class_name(model_id, intent_type)}",
            (cls,),
            {
                "intent_type": intent_type,
                "model_id": config.model_id,
                "default_model_kwargs": config.default_model_kwargs,
            }
        )
        return chain_class


def _import_chat_chain():
    from .chat_chain import chain_classes
    globals().update(chain_classes)
    from .chat_chain import (
        Internlm2Chat7BChatChain,
        Internlm2Chat20BChatChain,
        Baichuan2Chat13B4BitsChatChain,
    )


def _import_query_rewrite_chain():
    from .query_rewrite_chain import chain_classes
    globals().update(chain_classes)
    from .query_rewrite_chain import (
        Internlm2Chat20BQueryRewriteChain,
        Internlm2Chat7BQueryRewriteChain,
    )


def _import_rag_chain():
    from .rag_chain import chain_classes
    globals().update(chain_classes)
    from .rag_chain import (
        Baichuan2Chat13B4BitsKnowledgeQaChain,
    )


def _import_tool_calling_chain_api():
    from .tool_calling_chain_api import chain_classes
    globals().update(chain_classes)


def _import_conversation_summary_chain():
    from .conversation_summary_chain import (
        Internlm2Chat7BConversationSummaryChain,
        ClaudeInstanceConversationSummaryChain,
        Claude21ConversationSummaryChain,
        Claude3HaikuConversationSummaryChain,
        Claude3SonnetConversationSummaryChain,
        Internlm2Chat20BConversationSummaryChain,
        NovaProConversationSummaryChain
    )


def _import_intention_chain():
    from .intention_chain import (
        Claude21IntentRecognitionChain,
        Claude2IntentRecognitionChain,
        ClaudeInstanceIntentRecognitionChain,
        Claude3HaikuIntentRecognitionChain,
        Claude3SonnetIntentRecognitionChain,
        Internlm2Chat7BIntentRecognitionChain,
        Internlm2Chat20BIntentRecognitionChain,
    )


def _import_translate_chain():
    from .translate_chain import (
        Internlm2Chat7BTranslateChain,
        Internlm2Chat20BTranslateChain
    )


def _import_mkt_conversation_summary_chains():
    from marketing_chains.mkt_conversation_summary import (
        Claude21MKTConversationSummaryChain,
        ClaudeInstanceMKTConversationSummaryChain,
        Claude2MKTConversationSummaryChain,
        Claude3HaikuMKTConversationSummaryChain,
        Claude3SonnetMKTConversationSummaryChain,
        Internlm2Chat7BMKTConversationSummaryChain,
        Internlm2Chat20BMKTConversationSummaryChain
    )


def _import_mkt_rag_chain():
    from marketing_chains.mkt_rag_chain import (
        Internlm2Chat7BKnowledgeQaChain,
        Internlm2Chat20BKnowledgeQaChain
    )


def _import_stepback_chain():
    from .stepback_chain import (
        Claude21StepBackChain,
        ClaudeInstanceStepBackChain,
        Claude2StepBackChain,
        Claude3HaikuStepBackChain,
        Claude3SonnetStepBackChain,
        Internlm2Chat7BStepBackChain,
        Internlm2Chat20BStepBackChain
    )


def _import_hyde_chain():
    from .hyde_chain import (
        Claude21HydeChain,
        Claude2HydeChain,
        Claude3HaikuHydeChain,
        Claude3SonnetHydeChain,
        ClaudeInstanceHydeChain,
        Internlm2Chat20BHydeChain,
        Internlm2Chat7BHydeChain,
        NovaProHydeChain
    )


def _import_tool_calling_chain_claude_xml():
    from .tool_calling_chain_claude_xml import (
        Claude21ToolCallingChain,
        Claude3HaikuToolCallingChain,
        Claude2ToolCallingChain,
        Claude3SonnetToolCallingChain,
        ClaudeInstanceToolCallingChain,
        NovaProToolCallingChain
    )


def _import_retail_conversation_summary_chain():
    from .retail_chains.retail_conversation_summary_chain import (
        Claude2RetailConversationSummaryChain,
        Claude21RetailConversationSummaryChain,
        Claude3HaikuRetailConversationSummaryChain,
        Claude3SonnetRetailConversationSummaryChain,
        ClaudeInstanceRetailConversationSummaryChain
    )


def _import_retail_tool_calling_chain_claude_xml():
    from .retail_chains.retail_tool_calling_chain_claude_xml import (
        Claude2RetailToolCallingChain,
        Claude21RetailToolCallingChain,
        ClaudeInstanceRetailToolCallingChain,
        Claude3SonnetRetailToolCallingChain,
        Claude3HaikuRetailToolCallingChain
    )


def _import_auto_evaluation_chain():
    from .retail_chains.auto_evaluation_chain import (
        Claude3HaikuAutoEvaluationChain,
        Claude21AutoEvaluationChain,
        Claude2AutoEvaluationChain
    )


def _load_module(intent_type):
    assert intent_type in CHAIN_MODULE_LOAD_FN_MAP, (
        intent_type, CHAIN_MODULE_LOAD_FN_MAP)
    CHAIN_MODULE_LOAD_FN_MAP[intent_type]()


CHAIN_MODULE_LOAD_FN_MAP = {
    LLMTaskType.CHAT: _import_chat_chain,
    LLMTaskType.CONVERSATION_SUMMARY_TYPE: _import_conversation_summary_chain,
    LLMTaskType.INTENT_RECOGNITION_TYPE: _import_intention_chain,
    LLMTaskType.RAG: _import_rag_chain,
    LLMTaskType.QUERY_TRANSLATE_TYPE: _import_translate_chain,
    LLMTaskType.MKT_CONVERSATION_SUMMARY_TYPE: _import_mkt_conversation_summary_chains,
    LLMTaskType.MTK_RAG: _import_mkt_rag_chain,
    LLMTaskType.STEPBACK_PROMPTING_TYPE: _import_stepback_chain,
    LLMTaskType.HYDE_TYPE: _import_hyde_chain,
    LLMTaskType.QUERY_REWRITE_TYPE: _import_query_rewrite_chain,
    LLMTaskType.TOOL_CALLING_XML: _import_tool_calling_chain_claude_xml,
    LLMTaskType.TOOL_CALLING_API: _import_tool_calling_chain_api,
    LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE: _import_retail_conversation_summary_chain,
    LLMTaskType.RETAIL_TOOL_CALLING: _import_retail_tool_calling_chain_claude_xml,
    LLMTaskType.AUTO_EVALUATION: _import_auto_evaluation_chain
}

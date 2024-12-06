from typing import Any
from common_logic.common_utils.constant import LLMTaskType


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

def _import_chat_chain():
    from .chat_chain import (
    Claude2ChatChain,
    Claude21ChatChain,
    ClaudeInstanceChatChain,
    Internlm2Chat7BChatChain,
    Internlm2Chat20BChatChain,
    Baichuan2Chat13B4BitsChatChain,
    Claude3HaikuChatChain,
    Claude3SonnetChatChain,
    NovaProChatChain
)

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


def _import_rag_chain():
    from .rag_chain import (
    Claude21RagLLMChain,
    Claude2RagLLMChain,
    ClaudeInstanceRAGLLMChain,
    Claude3HaikuRAGLLMChain,
    Claude3SonnetRAGLLMChain,
    Baichuan2Chat13B4BitsKnowledgeQaChain,
    NovaProRAGLLMChain
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

def _import_query_rewrite_chain():
    from .query_rewrite_chain import (
    Claude21QueryRewriteChain,
    Claude2QueryRewriteChain,
    ClaudeInstanceQueryRewriteChain,
    Claude3HaikuQueryRewriteChain,
    Claude3SonnetQueryRewriteChain,
    Internlm2Chat20BQueryRewriteChain,
    Internlm2Chat7BQueryRewriteChain,
    NovaProQueryRewriteChain
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

def _import_tool_calling_chain_api():
    from .tool_calling_chain_api import (
        Claude21ToolCallingChain,
        Claude2ToolCallingChain,
        Claude35SonnetToolCallingChain,
        Claude3HaikuToolCallingChain,
        Claude3SonnetToolCallingChain,
        Llama31Instruct70BToolCallingChain,
        CohereCommandRPlusToolCallingChain,
        MistraLlarge2407ToolCallingChain,
        NovaProToolCallingChain,
    )


def _import_auto_evaluation_chain():
    from .retail_chains.auto_evaluation_chain import (
    Claude3HaikuAutoEvaluationChain,
    Claude21AutoEvaluationChain,
    Claude2AutoEvaluationChain

)


def _load_module(intent_type):
    assert intent_type in CHAIN_MODULE_LOAD_FN_MAP,(intent_type,CHAIN_MODULE_LOAD_FN_MAP)
    CHAIN_MODULE_LOAD_FN_MAP[intent_type]()


CHAIN_MODULE_LOAD_FN_MAP = {
    LLMTaskType.CHAT:_import_chat_chain,
    LLMTaskType.CONVERSATION_SUMMARY_TYPE:_import_conversation_summary_chain,
    LLMTaskType.INTENT_RECOGNITION_TYPE: _import_intention_chain,
    LLMTaskType.RAG: _import_rag_chain,
    LLMTaskType.QUERY_TRANSLATE_TYPE: _import_translate_chain,
    LLMTaskType.MKT_CONVERSATION_SUMMARY_TYPE: _import_mkt_conversation_summary_chains,
    LLMTaskType.MTK_RAG: _import_mkt_rag_chain,
    LLMTaskType.STEPBACK_PROMPTING_TYPE: _import_stepback_chain,
    LLMTaskType.HYDE_TYPE: _import_hyde_chain,
    LLMTaskType.QUERY_REWRITE_TYPE: _import_query_rewrite_chain,
    LLMTaskType.TOOL_CALLING_XML: _import_tool_calling_chain_claude_xml,
    LLMTaskType.TOOL_CALLING_API:_import_tool_calling_chain_api,
    LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE: _import_retail_conversation_summary_chain,
    LLMTaskType.RETAIL_TOOL_CALLING: _import_retail_tool_calling_chain_claude_xml,
    LLMTaskType.AUTO_EVALUATION: _import_auto_evaluation_chain
}

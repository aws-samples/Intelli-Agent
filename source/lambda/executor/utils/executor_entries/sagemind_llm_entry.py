import json
import logging
import math

from langchain.schema.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.base import message_to_dict

from .. import parse_config
from ..constant import MKT_CONVERSATION_SUMMARY_TYPE, IntentType
from ..ddb_utils import DynamoDBChatMessageHistory, filter_chat_history_by_time
from ..llm_utils import LLMChain
from ..serialization_utils import JSONEncoder

logger = logging.getLogger("market_conversation_summary_entry")
logger.setLevel(logging.INFO)


def sagemind_llm_entry(messages: list[dict], event_body=None, stream=False):
    config = parse_config.parse_sagemind_llm_config(event_body)
    logger.info(
        f"llm configs:\n {json.dumps(config,indent=2,ensure_ascii=False,cls=JSONEncoder)}"
    )
    # query_input = """请简要总结上述对话中的内容,每一个对话单独一个总结，并用 '- '开头。 每一个总结要先说明问题。\n"""
    llm_config = config["generator_llm_config"]
    llm_chain = LLMChain.get_chain(
        intent_type=IntentType.CHAT.value,
        stream=stream,
        **llm_config,
    )
    response = llm_chain.invoke({"query": "who are you", "chat_history": [""]})

    dict_chat_history = [message_to_dict(message) for message in config["chat_history"]]
    return response, [], dict_chat_history, {}

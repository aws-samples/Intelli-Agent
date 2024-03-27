import json
import logging
import math

from langchain.schema.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.base import message_to_dict

from .. import parse_config
from ..constant import MKT_CONVERSATION_SUMMARY_TYPE
from ..ddb_utils import DynamoDBChatMessageHistory, filter_chat_history_by_time
from ..llm_utils import LLMChain
from ..serialization_utils import JSONEncoder

logger = logging.getLogger("market_conversation_summary_entry")
logger.setLevel(logging.INFO)


def market_conversation_summary_entry(
    messages: list[dict], event_body=None, stream=False
):

    config = parse_config.parse_market_conversation_summary_entry_config(event_body)
    logger.info(
        f"market rag configs:\n {json.dumps(config,indent=2,ensure_ascii=False,cls=JSONEncoder)}"
    )
    if not config["chat_history"]:
        assert messages, messages
        chat_history = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            assert role in ["user", "ai"]
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            else:
                chat_history.append(AIMessage(content=content))
        config["chat_history"] = chat_history

    else:
        # filter by the window time
        time_window = config.get("time_window", {})
        start_time = time_window.get("start_time", -math.inf)
        end_time = time_window.get("end_time", math.inf)
        assert isinstance(start_time, float) and isinstance(end_time, float), (
            start_time,
            end_time,
        )
        chat_history = config["chat_history"]
        chat_history = filter_chat_history_by_time(
            chat_history, start_time=start_time, end_time=end_time
        )
        config["chat_history"] = chat_history
    
    if not config["chat_history"]:
        return f"该用户在所选时间段内历史消息为空。", [], [], {}
    # query_input = """请简要总结上述对话中的内容,每一个对话单独一个总结，并用 '- '开头。 每一个总结要先说明问题。\n"""
    mkt_conversation_summary_config = config["mkt_conversation_summary_config"]
    llm_chain = LLMChain.get_chain(
        intent_type=MKT_CONVERSATION_SUMMARY_TYPE,
        stream=stream,
        **mkt_conversation_summary_config,
    )
    response = llm_chain.invoke(
        {
            "chat_history": config["chat_history"],
        }
    )

    dict_chat_history = [message_to_dict(message) for message in config["chat_history"]]
    return response, [], dict_chat_history, {}

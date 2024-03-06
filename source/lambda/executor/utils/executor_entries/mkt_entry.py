import json
import logging
from .mkt_entry_core import market_chain_entry as market_chain_entry_core
from ..constant import AWS_TRANSLATE_SERVICE_MODEL_ID
from .. import parse_config

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

def market_chain_entry(
        query_input: str,
        stream=False,
        manual_input_intent=None,
        event_body=None,
        message_id=None
    ):
    rag_config = parse_config.parse_mkt_entry_config(event_body)
    return market_chain_entry_core(
        query_input,
        stream=stream,
        manual_input_intent=manual_input_intent,
        rag_config=rag_config,
        message_id=message_id
    )
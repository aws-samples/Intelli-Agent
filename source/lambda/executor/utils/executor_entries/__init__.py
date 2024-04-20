from ..constant import EntryType
from utils.parse_config import update_nest_dict

def get_main_chain_entry():
    from .common_entry import main_chain_entry
    return main_chain_entry

def get_text2sql_guidance_entry():
    from .text2sql_guidance_entry import text2sql_guidance_entry
    return text2sql_guidance_entry


def get_market_conversation_summary_entry():
    from .market_conversation_summary_entry import market_conversation_summary_entry
    return market_conversation_summary_entry


def get_market_chain_entry():
    from .mkt_knowledge_entry_langgraph import market_chain_knowledge_entry as market_chain_knowledge_entry_langgraph
    return market_chain_knowledge_entry_langgraph


def get_sagemind_llm_entry():
    from .sagemind_llm_entry import sagemind_llm_entry
    return sagemind_llm_entry

def drg_entry(event_body):
    event_body["llm_model_id"] = (
            event_body.get("llm_model_id", None)
            or "anthropic.claude-3-sonnet-20240229-v1:0"
        )
    dgr_config = {
        "retriever_config": {
            "qd_config": {
                "using_whole_doc": True,
                "qd_match_threshold": -100,
            },
            "workspace_ids": [
                "aos_index_repost_qq_m3",
                "aws-cn-dgr-user-guide-qd-m3-dense-20240318",
            ],
        },
        "generator_llm_config": {"context_num": 2},
    }
    market_entry = get_entry(EntryType.MARKET_CHAIN.value)

    event_body = update_nest_dict(dgr_config,event_body)
    return market_entry(
        event_body
    )

def get_dgr_entry():
    return drg_entry

entry_map = {
    EntryType.COMMON.value: get_main_chain_entry,
    EntryType.DGR.value: get_dgr_entry,
    EntryType.MARKET_CHAIN.value: get_market_chain_entry,
    EntryType.TEXT2SQL.value: get_text2sql_guidance_entry,
    EntryType.MARKET_CONVERSATION_SUMMARY.value: get_market_conversation_summary_entry
}

def get_entry(entry_name):
    return entry_map[entry_name]()
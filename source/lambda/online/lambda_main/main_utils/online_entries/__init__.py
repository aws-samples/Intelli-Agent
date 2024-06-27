from common_logic.common_utils.constant import EntryType

def get_common_entry():
    from .common_entry import main_chain_entry
    return main_chain_entry

def get_retail_entry():
    from .retail_entry import main_chain_entry
    return main_chain_entry

entry_map = {
    EntryType.COMMON: get_common_entry,
    EntryType.RETAIL: get_retail_entry
}

def get_entry(entry_name):
    return entry_map[entry_name]()

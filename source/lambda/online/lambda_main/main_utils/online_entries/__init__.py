from common_logic.common_utils.constant import EntryType

def get_common_entry():
    from .common_entry import main_chain_entry
    # init_common_tools()
    return main_chain_entry

entry_map = {
    EntryType.COMMON: get_common_entry
}

def get_entry(entry_name):
    return entry_map[entry_name]()

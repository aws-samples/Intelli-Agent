import collections.abc

def update_nest_dict(d:dict, u:dict):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def add_messages(left: list, right: list):
    """Add-don't-overwrite."""
    return left + right

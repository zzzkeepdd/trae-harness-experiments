def dedup(items):
    if items is None:
        return []
    seen = set()
    result = []
    for item in items:
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            result.append(item)
    return result

def flatten(nested):
    if nested is None:
        return []
    result = []
    for sublist in nested:
        if isinstance(sublist, list):
            result.extend(sublist)
        else:
            result.append(sublist)
    return result

def group_by(items, key_fn):
    if items is None:
        return {}
    groups = {}
    for item in items:
        key = key_fn(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups

def top_n(items, n, key_fn=None):
    if items is None:
        return []
    if key_fn is None:
        key_fn = lambda x: x
    if n <= 0:
        return []
    sorted_items = sorted(items, key=key_fn, reverse=True)
    return sorted_items[:n]

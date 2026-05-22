def dedup(items):
    if items is None:
        return []
    if not isinstance(items, list):
        raise TypeError("Expected a list")
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def flatten(nested):
    if nested is None:
        return []
    if not isinstance(nested, list):
        raise TypeError("Expected a list")
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result

def group_by(items, key_fn):
    if items is None:
        return {}
    if not isinstance(items, list):
        raise TypeError("Expected a list")
    if key_fn is None:
        raise TypeError("key_fn must be callable")
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
    if not isinstance(items, list):
        raise TypeError("Expected a list")
    if n <= 0:
        return []
    if n >= len(items):
        return list(items)
    if key_fn is None:
        key_fn = lambda x: x
    sorted_items = sorted(items, key=key_fn, reverse=True)
    return sorted_items[:n]

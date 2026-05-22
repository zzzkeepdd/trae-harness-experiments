def dedup(items):
    if items is None:
        return []
    if not isinstance(items, list):
        raise TypeError(f"Expected a list, got {type(items).__name__}")
    seen = set()
    result = []
    for item in items:
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            if item not in result:
                result.append(item)
    return result

def flatten(nested):
    if nested is None:
        return []
    if not isinstance(nested, list):
        raise TypeError(f"Expected a list, got {type(nested).__name__}")
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
        raise TypeError(f"Expected a list, got {type(items).__name__}")
    if not callable(key_fn):
        raise TypeError(f"key_fn must be callable, got {type(key_fn).__name__}")
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
        raise TypeError(f"Expected a list, got {type(items).__name__}")
    if not isinstance(n, int):
        raise TypeError(f"n must be int, got {type(n).__name__}")
    if n <= 0:
        return []
    if n >= len(items):
        return list(items)
    if key_fn is None:
        key_fn = lambda x: x
    return sorted(items, key=key_fn, reverse=True)[:n]

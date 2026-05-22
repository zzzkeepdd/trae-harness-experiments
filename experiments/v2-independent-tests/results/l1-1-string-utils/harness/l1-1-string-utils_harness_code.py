import re

def reverse(s):
    if s is None or s == "":
        return "" if s is None else s
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    return s[::-1]

def to_title_case(s):
    if s is None or s == "":
        return "" if s is None else s
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    words = s.strip().split()
    return " ".join(w[0].upper() + w[1:].lower() if w else "" for w in words)

def is_palindrome(s):
    if s is None:
        return False
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    if s == "":
        return False
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    if not cleaned:
        return False
    return cleaned == cleaned[::-1]

def word_count(s):
    if s is None or s == "":
        return {}
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", s.lower())
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts

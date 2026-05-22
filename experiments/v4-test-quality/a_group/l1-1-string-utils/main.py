import re

def reverse(s):
    if s is None:
        return ""
    return s[::-1]

def to_title_case(s):
    if s is None or s == "":
        return ""
    return s.title()

def is_palindrome(s):
    if s is None:
        return False
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    if not cleaned:
        return False
    return cleaned == cleaned[::-1]

def word_count(s):
    if s is None or s == "":
        return {}
    words = re.findall(r'[a-zA-Z0-9]+', s.lower())
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts

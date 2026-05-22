import re

def reverse(s):
    if s is None:
        raise TypeError("Input must be a string, not None")
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s[::-1]

def to_title_case(s):
    if s is None:
        raise TypeError("Input must be a string, not None")
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s.title()

def is_palindrome(s):
    if s is None:
        raise TypeError("Input must be a string, not None")
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    return cleaned == cleaned[::-1]

def word_count(s):
    if s is None:
        raise TypeError("Input must be a string, not None")
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    words = re.findall(r'\w+', s.lower())
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts

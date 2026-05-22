def text_search(text, pattern):
    if not pattern: return []
    n, m = len(text), len(pattern)
    matches = []
    for i in range(n - m + 1):
        match = True
        for j in range(m):
            if text[i+j] != pattern[j]:
                match = False
                break
        if match:
            matches.append(i)
    return matches

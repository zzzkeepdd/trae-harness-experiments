def _build_bad_char(pattern):
    m = len(pattern)
    bad = {}
    for i in range(m-1):
        bad[pattern[i]] = m - 1 - i
    return bad

def text_search(text, pattern):
    if not pattern: return []
    n, m = len(text), len(pattern)
    if m > n: return []
    bad = _build_bad_char(pattern)
    matches = []
    i = 0
    while i <= n - m:
        j = m - 1
        while j >= 0 and pattern[j] == text[i+j]:
            j -= 1
        if j < 0:
            matches.append(i)
            i += 1
        else:
            shift = bad.get(text[i+j], m)
            i += max(1, shift - (m - 1 - j))
    return matches

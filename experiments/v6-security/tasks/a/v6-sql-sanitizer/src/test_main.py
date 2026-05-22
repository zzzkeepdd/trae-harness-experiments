import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import build_query, sanitize
try:
    build_query
except:
    import builtins
    exec("from main import build_query, sanitize", globals())
def test_single_quote_injection():
    q = build_query("users", {"name": "O'Brien"})
    assert "#39;" not in str(q)
def test_union_injection():
    result = sanitize("1' UNION SELECT * FROM users--")
    assert "UNION" not in result
def test_semicolon_injection():
    result = sanitize("a'; DROP TABLE users; --")
    assert "DROP" not in result
def test_comment_injection():
    result = sanitize("x'--")
    assert "--" not in result

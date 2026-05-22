import sys, os, time; sys.path.insert(0, os.path.dirname(__file__))
from main import Cache

def test_basic():
    c = Cache(3)
    c.set("a", 1)
    assert c.get("a") == 1
    assert c.get("x") is None

def test_lru():
    c = Cache(2)
    c.set("a", 1); c.set("b", 2); c.get("a"); c.set("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1

def test_ttl():
    c = Cache(5)
    c.set("x", 99, ttl=0.05)
    assert c.get("x") == 99
    time.sleep(0.08)
    assert c.get("x") is None

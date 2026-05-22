import sys, os, time, threading; sys.path.insert(0, os.path.dirname(__file__))
from main import Cache

def test_set_get():
    c = Cache(3)
    c.set("a", 1)
    assert c.get("a") == 1
    assert c.get("x") is None
    c.set("a", 2)
    assert c.get("a") == 2

def test_lru_eviction():
    c = Cache(2)
    c.set("a", 1); c.set("b", 2)
    c.get("a")
    c.set("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3

def test_ttl():
    c = Cache(5)
    c.set("x", 99, ttl=0.05)
    assert c.get("x") == 99
    time.sleep(0.08)
    assert c.get("x") is None

def test_delete():
    c = Cache(10)
    c.set("a", 1); c.set("b", 2)
    c.delete("a")
    assert c.get("a") is None
    assert c.get("b") == 2
    c.delete("nonexistent")

def test_size_and_keys():
    c = Cache(5)
    assert c.size() == 0
    c.set("a", 1); c.set("b", 2)
    assert c.size() == 2
    assert sorted(c.keys()) == ["a", "b"]
    c.clear()
    assert c.size() == 0
    assert c.keys() == []

def test_max_size_validation():
    try:
        Cache(0)
        assert False, "should raise"
    except ValueError:
        pass
    try:
        Cache(-1)
        assert False, "should raise"
    except ValueError:
        pass

def test_concurrent():
    c = Cache(100)
    errors = []
    def writer(start, step):
        try:
            for i in range(start, start + 50):
                c.set(i, i * 2)
                c.get(i - 1)
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=writer, args=(i * 50, i)) for i in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(errors) == 0
    assert c.size() <= 100

def test_ttl_does_not_pollute_lru():
    c = Cache(3)
    c.set("a", 1, ttl=0.05)
    c.set("b", 2)
    c.set("c", 3)
    time.sleep(0.08)
    c.set("d", 4)
    assert c.get("a") is None
    assert c.get("b") == 2
    c.set("e", 5)
    assert c.get("b") is not None or c.get("c") is not None

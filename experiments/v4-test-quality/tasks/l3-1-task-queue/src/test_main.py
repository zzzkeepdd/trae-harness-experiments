import sys, os, time; sys.path.insert(0, os.path.dirname(__file__))
from main import Task, TaskQueue

def test_basic():
    q = TaskQueue(max_workers=2); q.start()
    q.submit(Task(priority=1, id="t1", func=lambda x: x * 2, args=(21,)))
    result = q.get_result("t1", timeout=5)
    assert result == 42
    q.stop()

def test_priority():
    q = TaskQueue(max_workers=1); q.start()
    results = []
    q.submit(Task(priority=1, id="lo", func=lambda: results.append("lo")))
    q.submit(Task(priority=10, id="hi", func=lambda: results.append("hi")))
    q.get_result("hi", timeout=5); q.get_result("lo", timeout=5)
    assert results[:2] == ["hi", "lo"]
    q.stop()

def test_timeout():
    q = TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=5, id="slow", func=lambda: time.sleep(10), max_retries=0, timeout=0.2))
    result = q.get_result("slow", timeout=5)
    assert isinstance(result, dict) and "error" in result
    q.stop()

def test_closed_rejects():
    q = TaskQueue(max_workers=1); q.start(); q.stop()
    try:
        q.submit(Task(priority=1, id="r", func=lambda: 1))
        assert False, "should raise"
    except RuntimeError:
        pass

def test_retry():
    calls = []
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("fail")
        return "ok"
    q = TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=1, id="flaky", func=flaky, max_retries=3))
    result = q.get_result("flaky", timeout=5)
    assert result == "ok"
    assert len(calls) == 3
    q.stop()

def test_invalid_workers():
    try:
        TaskQueue(max_workers=0)
        assert False
    except ValueError:
        pass

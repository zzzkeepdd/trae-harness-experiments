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

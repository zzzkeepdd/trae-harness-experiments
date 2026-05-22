import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import Task, TaskQueue
def test_no_sql_inject():
    q=TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=1, id="safe_1", func=lambda:42))
    assert q.get_result("safe_1",timeout=5)==42; q.stop()

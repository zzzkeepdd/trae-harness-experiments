import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import filter_rows, aggregate

def test_filter_rows():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    assert len(filter_rows(data, {"name": "Alice"})) == 1
    assert len(filter_rows(data, {"name": "X"})) == 0

def test_aggregate():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    result = aggregate(data, "name", {"op": "sum", "column": "score"})
    assert len(result) == 2

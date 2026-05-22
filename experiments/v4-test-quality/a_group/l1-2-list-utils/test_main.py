import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import dedup, flatten, group_by, top_n

def test_dedup():
    assert dedup([1, 2, 2, 3]) == [1, 2, 3]
    assert dedup([]) == []

def test_flatten():
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

def test_group_by():
    assert group_by(["a", "bb", "ddd"], len) == {1: ["a"], 2: ["bb"], 3: ["ddd"]}

def test_top_n():
    assert top_n([5, 3, 8, 1, 9], 2) == [9, 8]

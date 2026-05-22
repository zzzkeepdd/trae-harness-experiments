import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import dedup, flatten, group_by, top_n

def test_dedup():
    assert dedup([1, 2, 2, 3]) == [1, 2, 3]
    assert dedup([]) == []
    assert dedup(None) == []
    assert dedup([1, 2, 1, 3, 2, 4]) == [1, 2, 3, 4]
    assert dedup(["a", "b", "a"]) == ["a", "b"]
    assert dedup([{1: "a"}, {2: "b"}]) == [{1: "a"}, {2: "b"}]

def test_flatten():
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
    assert flatten([]) == []
    assert flatten(None) == []
    assert flatten([[1, [2, 3]], [4]]) == [1, [2, 3], 4]
    assert flatten([["a"], [], ["b"]]) == ["a", "b"]
    assert flatten([[1], "not_a_list", [2]]) == [1, "not_a_list", 2]

def test_group_by():
    assert group_by(["a", "bb", "ddd"], len) == {1: ["a"], 2: ["bb"], 3: ["ddd"]}
    assert group_by([], len) == {}
    assert group_by(None, len) == {}
    assert group_by([1, 2, 3, 4], lambda x: x % 2) == {1: [1, 3], 0: [2, 4]}
    assert group_by([1.5, 2.5, 3.5], lambda x: int(x)) == {1: [1.5], 2: [2.5], 3: [3.5]}

def test_top_n():
    assert top_n([5, 3, 8, 1, 9], 2) == [9, 8]
    assert top_n([5, 3, 8, 1, 9], 10) == [9, 8, 5, 3, 1]
    assert top_n(None, 3) == []
    assert top_n([], 3) == []
    assert top_n([5, 3, 8], 0) == []
    assert top_n([5, 3, 8], -1) == []
    assert top_n([{"v": 1}, {"v": 5}, {"v": 3}], 2, key_fn=lambda x: x["v"]) == [{"v": 5}, {"v": 3}]

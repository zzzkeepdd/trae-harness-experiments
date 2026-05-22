import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import sort_dedup
def test_sd():
    assert sort_dedup([3,1,2,3,1])==[1,2,3]; assert sort_dedup([])==[]; assert sort_dedup([5])==[5]
    assert sort_dedup([5,5,5])==[5]; assert sort_dedup([3,2,1])==[1,2,3]

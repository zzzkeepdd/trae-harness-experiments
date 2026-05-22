import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import text_search
def test_ts():
    assert text_search("hello world hello","hello")==[0,12]
    assert text_search("aaaa","aa")==[0,1,2]
    assert text_search("abc","xyz")==[]
    assert text_search("","abc")==[]
    assert text_search("abc","")==[]

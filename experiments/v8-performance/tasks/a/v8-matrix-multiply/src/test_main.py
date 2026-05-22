import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import matrix_multiply
def test_mm():
    a=[[1,2],[3,4]]; b=[[5,6],[7,8]]
    r=matrix_multiply(a,b); assert r[0]==[19,22]; assert r[1]==[43,50]
    assert matrix_multiply([[1,2]],[[3],[4]])==[[11]]

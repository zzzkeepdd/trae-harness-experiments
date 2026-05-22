import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import fibonacci, fibonacci_sequence
def test_fib():
    assert fibonacci(0)==0; assert fibonacci(1)==1; assert fibonacci(5)==5; assert fibonacci(10)==55
def test_seq():
    s=fibonacci_sequence(5); assert s==[0,1,1,2,3]

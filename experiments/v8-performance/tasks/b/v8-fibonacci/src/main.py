def fibonacci(n):
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n+1):
        a, b = b, a + b
    return b
def fibonacci_sequence(n):
    if n <= 0: return []
    seq = [0]
    a, b = 0, 1
    for _ in range(1, n):
        seq.append(b)
        a, b = b, a + b
    return seq

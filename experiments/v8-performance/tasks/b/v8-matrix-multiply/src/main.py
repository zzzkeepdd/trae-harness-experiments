def matrix_multiply(a, b):
    rows_a, cols_a = len(a), len(a[0]) if a else 0
    rows_b, cols_b = len(b), len(b[0]) if b else 0
    if cols_a != rows_b:
        raise ValueError("incompatible")
    b_cols = list(zip(*b))
    return [[sum(x*y for x,y in zip(row,col)) for col in b_cols] for row in a]

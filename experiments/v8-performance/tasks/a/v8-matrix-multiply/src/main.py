def matrix_multiply(a, b):
    rows_a, cols_a = len(a), len(a[0]) if a else 0
    rows_b, cols_b = len(b), len(b[0]) if b else 0
    if cols_a != rows_b:
        raise ValueError("incompatible")
    result = [[0.0]*cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for k in range(cols_a):
            aik = a[i][k]
            if aik != 0:
                for j in range(cols_b):
                    result[i][j] += aik * b[k][j]
    return result

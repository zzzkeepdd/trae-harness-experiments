def sort_dedup(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    result = []
    for x in arr:
        if x not in result:
            result.append(x)
    return result

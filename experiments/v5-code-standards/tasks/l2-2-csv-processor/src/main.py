import csv
import os

def read_csv(path, encoding="utf-8"):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []

def filter_rows(data, conditions):
    result = []
    for row in data:
        match = True
        for col, val in conditions.items():
            if col not in row or str(row[col]) != str(val):
                match = False
                break
        if match:
            result.append(row)
    return result

def aggregate(data, group_by, agg_fn):
    if not data:
        return []
    op = agg_fn.get("op", "sum")
    column = agg_fn.get("column")
    groups = {}
    for row in data:
        key = row.get(group_by)
        if key is None:
            continue
        if key not in groups:
            groups[key] = []
        val = row.get(column)
        if val is not None:
            try:
                groups[key].append(float(val))
            except (ValueError, TypeError):
                groups[key].append(0.0)
    result = []
    for key, vals in groups.items():
        entry = {group_by: key}
        if op == "sum":
            entry["sum"] = sum(vals)
        elif op == "count":
            entry["count"] = len(vals)
        elif op == "avg":
            entry["avg"] = sum(vals) / len(vals) if vals else 0
        elif op == "min":
            entry["min"] = min(vals) if vals else 0
        elif op == "max":
            entry["max"] = max(vals) if vals else 0
        result.append(entry)
    return result

def write_csv(data, path):
    if not data:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(data[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def process_pipeline(input_path, output_path, filter_cond, group_by_col, agg_col, agg_op):
    data = read_csv(input_path)
    filtered = filter_rows(data, filter_cond)
    aggregated = aggregate(filtered, group_by_col, {"op": agg_op, "column": agg_col})
    write_csv(aggregated, output_path)

import csv
import os
from pathlib import Path

def read_csv(path, encoding="utf-8"):
    if not os.path.isfile(path): return []
    try:
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            return [row for row in reader]
    except (UnicodeDecodeError, csv.Error): return []

def filter_rows(data, conditions):
    if not data: return []
    if not conditions: return data
    result = data
    for col, val in conditions.items():
        str_val = str(val)
        result = [row for row in result if row.get(col) == str_val]
    return result

def aggregate(data, group_by, agg_fn):
    if not data: return []
    op_col = agg_fn.get("column")
    op_name = agg_fn.get("op", "sum")
    groups = {}
    for row in data:
        key = row.get(group_by)
        if key is None: continue
        if key not in groups: groups[key] = []
        if op_col and op_col in row:
            try: groups[key].append(float(row[op_col]))
            except (ValueError, TypeError): pass
    results = []
    for key, vals in groups.items():
        if not vals: results.append({group_by: key, op_name: 0})
        elif op_name == "sum": results.append({group_by: key, op_name: sum(vals)})
        elif op_name == "count": results.append({group_by: key, op_name: len(vals)})
        elif op_name == "avg": results.append({group_by: key, op_name: sum(vals) / len(vals)})
        elif op_name == "min": results.append({group_by: key, op_name: min(vals)})
        elif op_name == "max": results.append({group_by: key, op_name: max(vals)})
    return results

def write_csv(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not data:
        with open(path, "w", encoding="utf-8", newline="") as f: pass
        return
    keys = list(data[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

def process_pipeline(input_path, output_path, filter_cond, group_by_col, agg_col, agg_op):
    data = read_csv(input_path)
    if filter_cond: data = filter_rows(data, filter_cond)
    if not data:
        write_csv([], output_path)
        return
    agg_fn = {"column": agg_col, "op": agg_op}
    result = aggregate(data, group_by_col, agg_fn)
    write_csv(result if result else [], output_path)

import csv
import os
from pathlib import Path

def read_csv(path, encoding="utf-8"):
    if not os.path.exists(path): return []
    try:
        with open(path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            return [row for row in reader]
    except Exception:
        return []

def filter_rows(data, conditions):
    if not data: return []
    filtered = data
    for col, val in conditions.items():
        filtered = [row for row in filtered if row.get(col) == str(val)]
    return filtered

def aggregate(data, group_by, agg_fn):
    if not data: return []
    groups = {}
    for row in data:
        key = row.get(group_by)
        if key is None: continue
        if key not in groups: groups[key] = []
        val = row.get(agg_fn.get("column", ""))
        if val is not None:
            try: groups[key].append(float(val))
            except (ValueError, TypeError): pass
    op = agg_fn.get("op", "sum")
    results = []
    for key, vals in groups.items():
        if not vals: results.append({group_by: key, op: 0})
        elif op == "sum": results.append({group_by: key, op: sum(vals)})
        elif op == "count": results.append({group_by: key, op: len(vals)})
        elif op == "avg": results.append({group_by: key, op: sum(vals) / len(vals)})
        elif op == "min": results.append({group_by: key, op: min(vals)})
        elif op == "max": results.append({group_by: key, op: max(vals)})
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
    agg_fn = {"column": agg_col, "op": agg_op}
    result = aggregate(data, group_by_col, agg_fn)
    write_csv(result, output_path)

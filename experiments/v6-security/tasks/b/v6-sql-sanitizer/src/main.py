import re

ALLOWED_IDENTIFIERS = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def build_query(table, conditions, allowed_columns=None):
    if not ALLOWED_IDENTIFIERS.match(table):
        raise ValueError("invalid table name")
    if not conditions:
        return f"SELECT * FROM {table}"
    params = []
    clauses = []
    for col, val in conditions.items():
        if not ALLOWED_IDENTIFIERS.match(col):
            raise ValueError(f"invalid column name: {col}")
        if allowed_columns is not None and col not in allowed_columns:
            raise ValueError(f"column not allowed: {col}")
        clauses.append(f"{col} = %s")
        params.append(str(val))
    return f"SELECT * FROM {table} WHERE " + " AND ".join(clauses), params

def sanitize(user_input):
    if user_input is None:
        return ""
    cleaned = re.sub(r"[\x00\x08\x0a\x0d\x1a;'\"]", "", str(user_input))
    return cleaned.strip()

def is_safe_input(user_input):
    dangerous = [";", "--", "/*", "*/", "xp_", "exec", "drop", "union select"]
    lower = str(user_input).lower()
    return not any(d in lower for d in dangerous)

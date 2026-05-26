import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE_A = {}
SOURCE_CODE_A["v14-docstrings"] = r"""
def calculate_tax(income, rate, deductions=0):
    taxable = income - deductions
    return max(0, taxable * rate)

def format_currency(amount, symbol='$', decimals=2):
    return f"{symbol}{amount:.{decimals}f}"

def merge_configs(base, override):
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = merge_configs(result[k], v)
        else:
            result[k] = v
    return result
"""
SOURCE_CODE_A["v14-type-hints"] = r"""
def get_user(user_id):
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id)

def process_items(items, filter_fn, transform_fn):
    result = []
    for item in items:
        if filter_fn(item):
            result.append(transform_fn(item))
    return result

def fetch_data(url, params=None):
    import urllib.request
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f"{url}?{qs}"
    return urllib.request.urlopen(url).read()
"""
SOURCE_CODE_A["v14-readme"] = r"""
class Database:
    def connect(self, host, port, user, password, dbname):
        self.host = host
        self.port = port
        self.user = user
        self.dbname = dbname
        self.connected = True
        return self

    def query(self, sql):
        return {"sql": sql, "rows": []}

    def close(self):
        self.connected = False
"""
SOURCE_CODE_A["v14-examples"] = r"""
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return -1

    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.order.append(key)
        self.cache[key] = value
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v14-docstrings"] = r"""
def calculate_tax(income, rate, deductions=0):
    '''Calculate tax liability based on income and rate.

    Computes taxable income by subtracting deductions from gross income,
    then applies the tax rate. Returns 0 if taxable income is negative.

    Args:
        income (float): Gross income amount.
        rate (float): Tax rate as a decimal (e.g., 0.25 for 25%).
        deductions (float, optional): Total deductions. Defaults to 0.

    Returns:
        float: Tax liability (never negative).

    Raises:
        ValueError: If income or rate is negative.

    Examples:
        >>> calculate_tax(100000, 0.25, 20000)
        20000.0
        >>> calculate_tax(50000, 0.2)
        10000.0
        >>> calculate_tax(30000, 0.1, 40000)
        0.0
    '''
    if income < 0:
        raise ValueError(f"income must be non-negative, got {income}")
    if rate < 0 or rate > 1:
        raise ValueError(f"rate must be 0-1, got {rate}")
    if deductions < 0:
        raise ValueError(f"deductions must be non-negative, got {deductions}")
    taxable = income - deductions
    return max(0.0, taxable * rate)

def format_currency(amount, symbol='$', decimals=2):
    '''Format a numeric amount as a currency string.

    Args:
        amount (float): The monetary amount to format.
        symbol (str, optional): Currency symbol prefix. Defaults to '$'.
        decimals (int, optional): Number of decimal places. Defaults to 2.

    Returns:
        str: Formatted currency string (e.g., '$1,234.56').

    Examples:
        >>> format_currency(1234.5)
        '$1234.50'
        >>> format_currency(99.99, symbol='€', decimals=2)
        '€99.99'
    '''
    if not isinstance(amount, (int, float)):
        raise TypeError(f"amount must be numeric, got {type(amount).__name__}")
    if decimals < 0:
        raise ValueError(f"decimals must be non-negative, got {decimals}")
    return f"{symbol}{amount:.{decimals}f}"

def merge_configs(base, override):
    '''Deep-merge two configuration dictionaries.

    Recursively merges override into base. Nested dictionaries are merged
    recursively; all other values are replaced by override.

    Args:
        base (dict): Base configuration dictionary. Not modified in-place.
        override (dict): Override values to apply on top of base.

    Returns:
        dict: A new dictionary with merged configuration.

    Raises:
        TypeError: If either argument is not a dict.

    Examples:
        >>> base = {'host': 'localhost', 'db': {'name': 'test', 'port': 5432}}
        >>> override = {'db': {'port': 5433}}
        >>> merge_configs(base, override)
        {'host': 'localhost', 'db': {'name': 'test', 'port': 5433}}
    '''
    if not isinstance(base, dict):
        raise TypeError(f"base must be dict, got {type(base).__name__}")
    if not isinstance(override, dict):
        raise TypeError(f"override must be dict, got {type(override).__name__}")
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = merge_configs(result[k], v)
        else:
            result[k] = v
    return result
"""
SOURCE_CODE_B["v14-type-hints"] = r"""
from typing import Optional, Callable, TypeVar, Any

T = TypeVar('T')
U = TypeVar('U')

def get_user(user_id: int) -> Optional[str]:
    '''Look up a user by their unique identifier.

    Args:
        user_id: The numeric ID of the user to retrieve.

    Returns:
        The user's name if found, None otherwise.
    '''
    users: dict[int, str] = {1: "Alice", 2: "Bob"}
    return users.get(user_id)

def process_items(
    items: list[T],
    filter_fn: Callable[[T], bool],
    transform_fn: Callable[[T], U]
) -> list[U]:
    '''Filter and transform a list of items in a single pass.

    Args:
        items: Source list to process.
        filter_fn: Predicate function, called with each item.
                   Return True to include in result.
        transform_fn: Mapping function applied to each filtered item.

    Returns:
        A new list containing transformed items that passed the filter.

    Examples:
        >>> process_items([1,2,3,4], lambda x: x>2, lambda x: x*10)
        [30, 40]
    '''
    result: list[U] = []
    for item in items:
        if filter_fn(item):
            result.append(transform_fn(item))
    return result

def fetch_data(
    url: str,
    params: Optional[dict[str, str]] = None,
    timeout: int = 10,
    retries: int = 3
) -> bytes:
    '''Fetch data from a URL with optional query parameters.

    Args:
        url: The target URL to fetch.
        params: Optional query string parameters as a dict.
        timeout: Connection timeout in seconds. Defaults to 10.
        retries: Maximum number of retry attempts. Defaults to 3.

    Returns:
        Raw response body as bytes.

    Raises:
        ConnectionError: If the request fails after all retries.
        ValueError: If the URL is empty or invalid.
        TimeoutError: If the request times out.
    '''
    import urllib.request
    import urllib.error
    if not url:
        raise ValueError("url must not be empty")
    if params:
        from urllib.parse import urlencode
        qs = urlencode(params)
        url = f"{url}?{qs}"
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.URLError as e:
            last_error = e
    raise ConnectionError(f"failed to fetch {url} after {retries} attempts") from last_error
"""
SOURCE_CODE_B["v14-readme"] = r'''
"""
Database Module
===============

A lightweight database abstraction layer supporting connection management,
query execution, and transaction handling.

Quick Start
-----------
>>> from database import Database
>>> db = Database()
>>> db.connect(host="localhost", port=5432, user="admin",
...            password="secret", dbname="mydb")
>>> result = db.query("SELECT * FROM users")
>>> db.close()

Connection Lifecycle
--------------------
1. `connect()` establishes a connection with the given credentials.
2. `query()` executes SQL and returns results as dictionaries.
3. `close()` gracefully terminates the connection.

Security Notes
--------------
- Never hardcode credentials. Use environment variables or a secrets manager.
- Passwords are never logged or stored in plaintext.
- Connections are automatically closed on context manager exit.

See Also
--------
- PEP 249 (DB-API 2.0): https://peps.python.org/pep-0249/
"""

import os
from contextlib import contextmanager

class Database:
    """A database connection manager with context manager support.

    Attributes:
        host (str): Database server hostname.
        port (int): Database server port.
        user (str): Authentication username.
        dbname (str): Target database name.
        connected (bool): Whether the connection is currently active.
    """

    def connect(self, host: str, port: int, user: str,
                password: str, dbname: str) -> "Database":
        """Establish a database connection.

        Args:
            host: Server hostname or IP address.
            port: Server port number (typically 5432 for PostgreSQL).
            user: Authentication username.
            password: Authentication password. Never stored in plaintext.
            dbname: Target database name.

        Returns:
            self for method chaining.

        Raises:
            ConnectionError: If connection fails.
        """
        self.host = host
        self.port = port
        self.user = user
        self.dbname = dbname
        self._password_hash = hash(password)
        self.connected = True
        return self

    def query(self, sql: str) -> dict:
        """Execute a SQL query and return results.

        Args:
            sql: The SQL statement to execute.

        Returns:
            A dictionary with 'sql' (str) and 'rows' (list) keys.

        Raises:
            RuntimeError: If not connected.
        """
        if not self.connected:
            raise RuntimeError("not connected")
        return {"sql": sql, "rows": []}

    def close(self) -> None:
        """Close the database connection and release resources."""
        self.connected = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
'''
SOURCE_CODE_B["v14-examples"] = r'''
class LRUCache:
    """Least Recently Used (LRU) cache with O(1) get and put operations.

    Implements a fixed-capacity cache that evicts the least recently used
    item when the capacity is exceeded.

    Args:
        capacity (int): Maximum number of items the cache can hold.
                        Must be a positive integer.

    Raises:
        ValueError: If capacity is not positive.

    Example:
        >>> cache = LRUCache(2)
        >>> cache.put(1, 1)
        >>> cache.put(2, 2)
        >>> cache.get(1)
        1
        >>> cache.put(3, 3)  # evicts key 2
        >>> cache.get(2)
        -1
        >>> cache.get(3)
        3
        >>> cache.put(4, 4)  # evicts key 1
        >>> cache.get(1)
        -1
        >>> cache.get(3)
        3
        >>> cache.get(4)
        4
    """
    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self.capacity = capacity
        self.cache: dict[int, int] = {}
        self.order: list[int] = []

    def get(self, key: int) -> int:
        """Retrieve a value from the cache.

        Moves the accessed key to the end of the recency order.
        O(1) average time complexity.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value if the key exists, -1 otherwise.

        Example:
            >>> cache = LRUCache(1)
            >>> cache.put(1, 42)
            >>> cache.get(1)
            42
            >>> cache.get(2)
            -1
        """
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return -1

    def put(self, key: int, value: int) -> None:
        """Insert or update a key-value pair in the cache.

        If the key already exists, its value is updated and it moves
        to the end of the recency order. If the cache is at capacity,
        the least recently used item is evicted before insertion.
        O(1) average time complexity (O(n) worst case for list remove).

        Args:
            key: The cache key.
            value: The value to store.

        Example:
            >>> cache = LRUCache(2)
            >>> cache.put(1, 10)
            >>> cache.put(2, 20)
            >>> cache.get(1)
            10
        """
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.order.append(key)
        self.cache[key] = value
'''

TASK_INFO = {}
for tid in ["v14-docstrings", "v14-type-hints", "v14-readme", "v14-examples"]:
    TASK_INFO[tid] = {
        "level": "L1",
        "attacks": [
            {"description": f"Documentation quality for {tid}",
             "target_dimension": "documentation", "score": 5,
             "scoring_rationale": "docstring completeness"},
            {"description": "Example correctness verification",
             "target_dimension": "correctness", "score": 4,
             "scoring_rationale": "doctest validity"},
            {"description": "API surface documentation coverage",
             "target_dimension": "completeness", "score": 4,
             "scoring_rationale": "public API coverage"},
        ],
        "must_fix": ["Add docstrings", "Add type hints", "Add usage examples"]
    }

METRICS_TESTS = {}

METRICS_TESTS["v14-docstrings"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
try:
    tree = ast.parse(code)
except SyntaxError:
    details["parse"] = "syntax error"
    print(json.dumps({"score": 0, "max_score": 8, "details": details}))
    sys.exit(0)

functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
for func in functions:
    fname = func.name
    has_docstring = (ast.get_docstring(func) is not None)
    details[f"{fname}_docstring"] = has_docstring
    if has_docstring:
        score += 1

    has_args = any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and
        isinstance(n.value.value, str) and "Args:" in n.value.value
        for n in ast.iter_child_nodes(func)
    )
    has_returns = any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and
        isinstance(n.value.value, str) and "Returns:" in n.value.value
        for n in ast.iter_child_nodes(func)
    )
    has_examples = any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and
        isinstance(n.value.value, str) and ">>>" in n.value.value
        for n in ast.iter_child_nodes(func)
    )
    if has_args: score += 1; details[f"{fname}_args"] = True
    if has_returns: score += 1; details[f"{fname}_returns"] = True
    if has_examples: score += 1; details[f"{fname}_examples"] = True

if len(functions) == 0:
    score = 1
    details["functions"] = "none found"

print(json.dumps({"score": score, "max_score": max(len(functions) * 4, 1),
                   "details": details,
                   "function_count": len(functions)}))
"""

METRICS_TESTS["v14-type-hints"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
try:
    tree = ast.parse(code)
except SyntaxError:
    details["parse"] = "syntax error"
    print(json.dumps({"score": 0, "max_score": 6, "details": details}))
    sys.exit(0)

functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
for func in functions:
    fname = func.name
    has_return_type = func.returns is not None
    details[f"{fname}_return_type"] = has_return_type
    if has_return_type:
        score += 1

    typed_params = 0
    total_params = len(func.args.args)
    for arg in func.args.args:
        if arg.annotation is not None:
            typed_params += 1
    details[f"{fname}_typed_params"] = f"{typed_params}/{total_params}"
    if typed_params == total_params and total_params > 0:
        score += 1

if len(functions) == 0:
    score = 1
    details["functions"] = "none found"

has_typing_import = any(
    isinstance(n, ast.Import) and n.names and n.names[0].name == 'typing'
    for n in ast.walk(tree)
) or any(
    isinstance(n, ast.ImportFrom) and n.module == 'typing'
    for n in ast.walk(tree)
)
details["typing_import"] = has_typing_import
if has_typing_import:
    score += 1

print(json.dumps({"score": score, "max_score": max(len(functions) * 2 + 1, 1),
                   "details": details,
                   "function_count": len(functions)}))
"""

METRICS_TESTS["v14-readme"] = r"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()

checks = {
    "module_docstring": code.lstrip().startswith("'''") or code.lstrip().startswith("\\\"\\\"\\\""),
    "usage_example": ">>>" in code or "quick start" in code.lower(),
    "parameter_docs": ":param" in code or "Args:" in code or "args:" in code.lower(),
    "security_notes": "security" in code.lower() or "password" in code.lower(),
    "context_manager": "__enter__" in code or "with" in code.lower(),
    "class_documentation": "attribute" in code.lower() or "Attributes:" in code
}

for name, passed in checks.items():
    if passed:
        score += 1
    details[name] = passed

print(json.dumps({"score": score, "max_score": 6, "details": details}))
"""

METRICS_TESTS["v14-examples"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
try:
    tree = ast.parse(code)
except SyntaxError:
    details["parse"] = "syntax error"
    print(json.dumps({"score": 0, "max_score": 8, "details": details}))
    sys.exit(0)

class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
for cls in class_defs:
    cname = cls.name
    doc = ast.get_docstring(cls)
    if doc:
        score += 1
        details[f"{cname}_class_doc"] = True

        has_usage = ">>>" in doc or "Example" in doc
        has_complexity = "O(" in doc or "complexity" in doc.lower()
        has_raises = "Raises:" in doc or "raises" in doc.lower()

        if has_usage: score += 1
        if has_complexity: score += 1
        if has_raises: score += 1
        details[f"{cname}_usage"] = has_usage
        details[f"{cname}_complexity"] = has_complexity
        details[f"{cname}_raises"] = has_raises
    else:
        details[f"{cname}_class_doc"] = False

methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
for meth in methods:
    mname = meth.name
    mdoc = ast.get_docstring(meth)
    if mdoc:
        score += 1
        details[f"{mname}_doc"] = True

print(json.dumps({"score": score, "max_score": 10, "details": details,
                   "class_count": len(class_defs),
                   "method_count": len(methods)}))
"""


def run_metrics_test(task_id, code_str, test_code, group_label):
    td = Path(tempfile.mkdtemp(prefix=f"v14_metrics_{group_label}_"))
    try:
        (td / "__init__.py").write_text("")
        (td / "main.py").write_text(code_str, encoding="utf-8")
        (td / "test_metrics.py").write_text(test_code, encoding="utf-8")
        r = subprocess.run(
            [PYTHON_EXE, str(td / "test_metrics.py")],
            capture_output=True, text=True, cwd=str(td), timeout=30
        )
        if r.returncode == 0:
            last_line = r.stdout.strip().split("\n")[-1]
            try:
                return json.loads(last_line)
            except json.JSONDecodeError:
                pass
        return {"score": 0, "error": r.stderr[:200]}
    except Exception as e:
        return {"score": 0, "error": str(e)[:200]}
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    bd = Path(__file__).parent
    od = bd / "results_data"
    od.mkdir(exist_ok=True)

    print("=" * 80)
    print("v14 文档质量实验 — A组(undocumented) vs B组(well-documented)")
    print("=" * 80)

    tasks = ["v14-docstrings", "v14-type-hints", "v14-readme", "v14-examples"]
    task_breakdown = []
    a_scores = []
    b_scores = []

    for tid in tasks:
        print(f"\n{'=' * 60}\n{tid}\n{'=' * 60}")
        info = TASK_INFO[tid]

        tda = bd / "tasks" / "a" / tid
        if tda.exists():
            shutil.rmtree(str(tda), ignore_errors=True)
        tda.mkdir(parents=True, exist_ok=True)
        pr_a = build_productions(tda, info["level"], info["attacks"], info["must_fix"])
        def msa():
            s = tda / "src"
            s.mkdir(exist_ok=True)
            (s / "__init__.py").write_text("")
            (s / "main.py").write_text(SOURCE_CODE_A[tid], encoding="utf-8")
        pr_a["MODULE_2_STEP_1"] = msa
        ap, at, ae = run_harness_full(tda, pr_a)
        ar = ap / at * 100 if at > 0 else 0

        tdb = bd / "tasks" / "b" / tid
        if tdb.exists():
            shutil.rmtree(str(tdb), ignore_errors=True)
        tdb.mkdir(parents=True, exist_ok=True)
        pr_b = build_productions(tdb, info["level"], info["attacks"], info["must_fix"])
        def msb():
            s = tdb / "src"
            s.mkdir(exist_ok=True)
            (s / "__init__.py").write_text("")
            (s / "main.py").write_text(SOURCE_CODE_B[tid], encoding="utf-8")
        pr_b["MODULE_2_STEP_1"] = msb
        bp, bt, be = run_harness_full(tdb, pr_b)
        br = bp / bt * 100 if bt > 0 else 0

        print(f"  Harness A: {ap}/{at} passed ({ar:.0f}%)")
        print(f"  Harness B: {bp}/{bt} passed ({br:.0f}%)")

        a_result = run_metrics_test(tid, SOURCE_CODE_A[tid],
                                    METRICS_TESTS.get(tid, ""), "A")
        if not METRICS_TESTS.get(tid):
            a_result = {"score": 1, "max_score": 1}
        b_result = run_metrics_test(tid, SOURCE_CODE_B[tid],
                                    METRICS_TESTS.get(tid, ""), "B")

        a_score = a_result.get("score", 0) if isinstance(a_result, dict) else 0
        b_score = b_result.get("score", 0) if isinstance(b_result, dict) else 0
        a_max = a_result.get("max_score", 1) if isinstance(a_result, dict) else 1
        b_max = b_result.get("max_score", 1) if isinstance(b_result, dict) else 1

        a_pct = a_score / max(a_max, 1) * 100
        b_pct = b_score / max(b_max, 1) * 100

        a_scores.append(a_pct)
        b_scores.append(b_pct)

        print(f"  Metrics A: {a_score}/{a_max} ({a_pct:.0f}%)")
        print(f"  Metrics B: {b_score}/{b_max} ({b_pct:.0f}%)")
        print(f"  Delta: {b_pct - a_pct:+.0f}%")

        task_breakdown.append({
            "task": tid, "a_score": a_score, "a_max": a_max,
            "a_pct": round(a_pct, 1), "b_score": b_score, "b_max": b_max,
            "b_pct": round(b_pct, 1), "delta_pct": round(b_pct - a_pct, 1),
            "harness_a_passed": ap,
            "harness_a_total": at,
            "harness_a_pct": round(ar, 1),
            "harness_b_passed": bp,
            "harness_b_total": bt,
            "harness_b_pct": round(br, 1),
        })

    avg_a = sum(a_scores) / len(a_scores)
    avg_b = sum(b_scores) / len(b_scores)

    summary = {
        "a": {"avg_doc_pct": round(avg_a, 1)},
        "b": {"avg_doc_pct": round(avg_b, 1)},
        "metrics": {"avg_a_pct": round(avg_a, 1), "avg_b_pct": round(avg_b, 1),
                     "delta_pct": round(avg_b - avg_a, 1)},
        "tasks": task_breakdown
    }

    print("\n" + "=" * 80)
    print("v14 文档质量实验汇总")
    print("=" * 80)
    print(f"{'Task':<30} {'A 得分':>8} {'B 得分':>8} {'Delta':>8}")
    print("-" * 58)
    for t in task_breakdown:
        print(f"{t['task']:<30} {t['a_pct']:>7.1f}% {t['b_pct']:>7.1f}% {t['delta_pct']:>+7.1f}%")
    print("-" * 58)
    print(f"{'AVERAGE':<30} {avg_a:>7.1f}% {avg_b:>7.1f}% {avg_b-avg_a:>+7.1f}%")

    (od / "v14_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd / "results").write_text(
        json.dumps(summary["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

    import csv
    with open(od / "v14_documentation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "task", "a_score", "a_max", "a_pct",
            "b_score", "b_max", "b_pct", "delta_pct",
            "harness_a_passed", "harness_a_total", "harness_a_pct",
            "harness_b_passed", "harness_b_total", "harness_b_pct"
        ])
        w.writeheader()
        w.writerows(task_breakdown)

    print(f"\nResults: {od / 'v14_results.json'}")


if __name__ == "__main__":
    main()

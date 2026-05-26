import sys, json, time, os, tempfile, subprocess, shutil, re, ast, math
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE_A = {}
SOURCE_CODE_A["v15-dry-violation"] = r"""
def format_email(name, domain, template="{}@{}"):
    return template.format(name, domain)

def create_user_email(first_name, last_name, domain):
    username = f"{first_name}.{last_name}".lower()
    return format_email(username, domain)

def create_admin_email(full_name, domain):
    username = full_name.replace(" ", ".").lower()
    return format_email(username, domain)

def send_welcome(email, company_name):
    body = f"Welcome to {company_name}, {email}"
    return body

def send_goodbye(email):
    body = f"Goodbye {email}"
    return body
"""
SOURCE_CODE_A["v15-circular-deps"] = r"""
class UserService:
    def __init__(self, order_service):
        self.order_service = order_service
    def get_user_orders(self, user_id):
        return self.order_service.get_orders(user_id)

class OrderService:
    def __init__(self, user_service):
        self.user_service = user_service
    def get_order_with_user(self, order_id):
        orders = {"1": {"id": 1, "user_id": 100, "amount": 50}}
        order = orders.get(str(order_id), {})
        user = self.user_service.get_user(order.get("user_id"))
        return {"order": order, "user": user}
    def get_orders(self, user_id):
        return [{"id": 1, "user_id": user_id}]
"""
SOURCE_CODE_A["v15-deep-nesting"] = r"""
def process_order(order):
    if order is not None:
        if "items" in order:
            if len(order["items"]) > 0:
                total = 0
                for item in order["items"]:
                    if "price" in item and "qty" in item:
                        if item["price"] > 0:
                            total += item["price"] * item["qty"]
                if total > 0:
                    if "discount" in order and order["discount"] > 0:
                        total *= (1 - order["discount"])
                    order["total"] = total
                    return order
    return None
"""
SOURCE_CODE_A["v15-god-class"] = r"""
class AppManager:
    def __init__(self):
        self.users = {}
        self.orders = {}
        self.products = {}
        self.settings = {"theme": "dark", "lang": "en"}

    def add_user(self, uid, name): self.users[uid] = name
    def get_user(self, uid): return self.users.get(uid)
    def delete_user(self, uid): self.users.pop(uid, None)

    def place_order(self, oid, uid, items):
        self.orders[oid] = {"user_id": uid, "items": items, "status": "pending"}

    def get_order(self, oid): return self.orders.get(oid)
    def cancel_order(self, oid):
        if oid in self.orders:
            self.orders[oid]["status"] = "cancelled"

    def add_product(self, pid, name, price):
        self.products[pid] = {"name": name, "price": price}

    def get_product(self, pid): return self.products.get(pid)
    def list_products(self): return list(self.products.values())

    def update_settings(self, key, value):
        self.settings[key] = value

    def get_settings(self): return self.settings
    def export_report(self):
        return {"users": len(self.users), "orders": len(self.orders),
                "products": len(self.products), "settings": self.settings}

    def backup_data(self):
        return {"users": self.users, "orders": self.orders,
                "products": self.products, "settings": self.settings}
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v15-dry-violation"] = r"""
from typing import Callable

def format_email(username: str, domain: str,
                 template: str = "{}@{}") -> str:
    return template.format(username, domain)

def _build_username(first_name: str, last_name: str) -> str:
    return f"{first_name}.{last_name}".lower()

def create_user_email(first_name: str, last_name: str,
                      domain: str) -> str:
    return format_email(_build_username(first_name, last_name), domain)

def create_admin_email(full_name: str, domain: str) -> str:
    username = full_name.replace(" ", ".").lower()
    return format_email(username, domain)

_EMAIL_TEMPLATES = {
    "welcome": "Welcome to {company}, {email}",
    "goodbye": "Goodbye {email}",
    "reset": "Password reset link for {email}",
}

def _render_email(template_key: str, **kwargs) -> str:
    template = _EMAIL_TEMPLATES.get(template_key)
    if template is None:
        raise ValueError(f"unknown template: {template_key}")
    return template.format(**kwargs)

def send_welcome(email: str, company_name: str) -> str:
    return _render_email("welcome", company=company_name, email=email)

def send_goodbye(email: str) -> str:
    return _render_email("goodbye", email=email)

def send_password_reset(email: str) -> str:
    return _render_email("reset", email=email)
"""
SOURCE_CODE_B["v15-circular-deps"] = r"""
from typing import Optional, Any
from abc import ABC, abstractmethod

class UserProtocol(ABC):
    @abstractmethod
    def get_user(self, user_id: int) -> Optional[dict]:
        ...

class OrderStore:
    def __init__(self):
        self._orders = {"1": {"id": 1, "user_id": 100, "amount": 50}}

    def get_orders_by_user(self, user_id: int) -> list:
        return [o for o in self._orders.values() if o.get("user_id") == user_id]

    def get_order(self, order_id: int) -> Optional[dict]:
        return self._orders.get(str(order_id))

class OrderService:
    def __init__(self, order_store: OrderStore,
                 user_service: Optional[UserProtocol] = None):
        self._store = order_store
        self._user_service = user_service

    def get_orders(self, user_id: int) -> list:
        return self._store.get_orders_by_user(user_id)

    def get_order_with_user(self, order_id: int) -> dict:
        order = self._store.get_order(order_id) or {}
        user = None
        if self._user_service and order.get("user_id"):
            user = self._user_service.get_user(order["user_id"])
        return {"order": order, "user": user}

class UserService:
    def __init__(self, order_service: Optional[OrderService] = None):
        self._users = {100: {"id": 100, "name": "Alice"}}
        self._order_service = order_service

    def get_user(self, user_id: int) -> Optional[dict]:
        return self._users.get(user_id)

    def get_user_orders(self, user_id: int) -> list:
        if self._order_service:
            return self._order_service.get_orders(user_id)
        return []

class ServiceContainer:
    def __init__(self):
        self._order_store = OrderStore()
        self._order_service: Optional[OrderService] = None
        self._user_service: Optional[UserService] = None

    def build(self):
        self._order_service = OrderService(self._order_store)
        self._user_service = UserService(self._order_service)
        self._order_service._user_service = self._user_service
        return self._user_service, self._order_service
"""
SOURCE_CODE_B["v15-deep-nesting"] = r"""
from typing import Optional, Any

def process_order(order: dict) -> Optional[dict]:
    if order is None:
        return None

    items = order.get("items")
    if not items:
        return None

    total = _calculate_item_total(items)
    if total <= 0:
        return None

    total = _apply_discount(total, order.get("discount"))
    return {**order, "total": total}

def _calculate_item_total(items: list) -> float:
    total = 0.0
    for item in items:
        total += _item_subtotal(item)
    return total

def _item_subtotal(item: dict) -> float:
    price = item.get("price", 0)
    qty = item.get("qty", 0)
    if not isinstance(price, (int, float)) or price <= 0:
        return 0.0
    if not isinstance(qty, (int, float)) or qty <= 0:
        return 0.0
    return price * qty

def _apply_discount(total: float, discount: Any) -> float:
    if isinstance(discount, (int, float)) and 0 < discount < 1:
        return total * (1 - discount)
    return total
"""
SOURCE_CODE_B["v15-god-class"] = r"""
from typing import Optional, Any

class UserRepository:
    def __init__(self):
        self._users: dict[int, str] = {}

    def add(self, uid: int, name: str) -> None:
        self._users[uid] = name

    def get(self, uid: int) -> Optional[str]:
        return self._users.get(uid)

    def delete(self, uid: int) -> None:
        self._users.pop(uid, None)

class OrderRepository:
    def __init__(self):
        self._orders: dict[int, dict] = {}

    def create(self, oid: int, user_id: int, items: list) -> None:
        self._orders[oid] = {
            "user_id": user_id, "items": items, "status": "pending"}

    def get(self, oid: int) -> Optional[dict]:
        return self._orders.get(oid)

    def update_status(self, oid: int, status: str) -> bool:
        if oid in self._orders:
            self._orders[oid]["status"] = status
            return True
        return False

class ProductRepository:
    def __init__(self):
        self._products: dict[int, dict] = {}

    def add(self, pid: int, name: str, price: float) -> None:
        self._products[pid] = {"name": name, "price": price}

    def get(self, pid: int) -> Optional[dict]:
        return self._products.get(pid)

    def list_all(self) -> list:
        return list(self._products.values())

class SettingsManager:
    _DEFAULTS = {"theme": "dark", "lang": "en"}

    def __init__(self):
        self._settings = dict(self._DEFAULTS)

    def update(self, key: str, value: Any) -> None:
        self._settings[key] = value

    def get_all(self) -> dict:
        return dict(self._settings)

class ReportGenerator:
    def __init__(self, user_repo: UserRepository,
                 order_repo: OrderRepository,
                 product_repo: ProductRepository,
                 settings: SettingsManager):
        self._user_repo = user_repo
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._settings = settings

    def generate_summary(self) -> dict:
        return {
            "users": len(self._user_repo._users),
            "orders": len(self._order_repo._orders),
            "products": len(self._product_repo._products),
            "settings": self._settings.get_all()
        }

class AppManager:
    def __init__(self):
        self.users = UserRepository()
        self.orders = OrderRepository()
        self.products = ProductRepository()
        self.settings = SettingsManager()
        self.reports = ReportGenerator(
            self.users, self.orders, self.products, self.settings)
"""

TASK_INFO = {}
for tid in ["v15-dry-violation", "v15-circular-deps", "v15-deep-nesting", "v15-god-class"]:
    level = "L2" if tid in ("v15-circular-deps", "v15-god-class") else "L1"
    TASK_INFO[tid] = {
        "level": level,
        "attacks": [
            {"description": f"Maintainability analysis for {tid}",
             "target_dimension": "maintainability", "score": 5,
             "scoring_rationale": "code structure quality"},
            {"description": "Code smell detection",
             "target_dimension": "code_quality", "score": 4,
             "scoring_rationale": "anti-pattern detection"},
            {"description": "Refactoring safety verification",
             "target_dimension": "safety", "score": 4,
             "scoring_rationale": "refactoring impact"},
        ],
        "must_fix": ["Reduce complexity", "Improve code structure"]
    }


def calc_cyclomatic_complexity(code: str) -> float:
    tree = ast.parse(code)
    complexity = 0
    node_count = 0
    for node in ast.walk(tree):
        node_count += 1
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            complexity += sum(1 for clause in node.ifs) + 1
    return complexity if node_count > 0 else 0


def calc_method_count(code: str) -> int:
    tree = ast.parse(code)
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))


def calc_class_count(code: str) -> int:
    tree = ast.parse(code)
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))


def calc_nesting_depth(code: str) -> int:
    tree = ast.parse(code)
    max_depth = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            depth = 0
            current = node
            while hasattr(current, 'parent'):
                depth += 1
                current = current.parent
            max_depth = max(max_depth, depth)

    indent_max = 0
    for line in code.split('\n'):
        indent = len(line) - len(line.lstrip())
        indent_max = max(indent_max, indent)
    return max(1, indent_max // 4)


def calc_maintainability_index(code: str) -> float:
    lines = len([l for l in code.split('\n') if l.strip()])
    cc = max(calc_cyclomatic_complexity(code), 0.1)
    loc = max(lines, 1)
    mi = max(0, (171 - 5.2 * math.log(cc) - 0.23 * cc - 16.2 * math.log(loc)) * 100 / 171)
    return round(mi, 1)


METRICS_TESTS = {}

METRICS_TESTS["v15-dry-violation"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
tree = ast.parse(code)

functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
bodies = {}
for f in functions:
    body_str = ast.unparse(f) if hasattr(ast, 'unparse') else ast.dump(f)
    bodies[f.name] = body_str

dedup_wins = 0
has_template_system = False
has_central_format = False
for name, body in bodies.items():
    if "_render_email" in name or "_build_username" in name:
        has_central_format = True
    if "_templates" in code.lower() or "_EMAIL_TEMPLATES" in code:
        has_template_system = True
    duplicate = any(
        name != f.name and _similarity(body, ast.unparse(f) if hasattr(ast, 'unparse') else '') > 0.7
        for f in functions
    )
    if not duplicate:
        dedup_wins += 1

def _similarity(a, b):
    if not a or not b: return 0
    return len(set(a.split()) & set(b.split())) / max(len(set(a.split())), 1)

mi = 0
try:
    lines = len(code.strip().split('\\n'))
    cc = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.If, ast.While, ast.For)))
    import math
    mi = max(0, (171 - 5.2 * math.log(max(cc, 0.1)) - 0.23 * cc - 16.2 * math.log(max(lines, 1))) * 100 / 171)
except: pass

checks = {
    "template_system": has_template_system,
    "central_format_func": has_central_format,
    "no_duplicate_code": dedup_wins >= len(functions) - 1,
}

for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

score += min(2, int(dedup_wins / 2))
details["dedup_score"] = dedup_wins

results = {"score": score, "max_score": 5, "details": details, "maintainability_index": round(mi, 1)}
print(json.dumps(results))
"""

METRICS_TESTS["v15-circular-deps"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
tree = ast.parse(code)

class_defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}

def _find_init_deps(cls_node):
    deps = set()
    for n in ast.walk(cls_node):
        if isinstance(n, ast.FunctionDef) and n.name == '__init__':
            for stmt in ast.walk(n):
                if isinstance(stmt, ast.AnnAssign) or isinstance(stmt, ast.Assign):
                    pass
            for child in ast.walk(n):
                if isinstance(child, ast.Name):
                    if child.id[0].isupper():
                        deps.add(child.id)
            break
    return deps

has_circular = False
for name, cls in class_defs.items():
    deps = _find_init_deps(cls)
    details[name] = list(deps)
    for other in class_defs:
        if other != name and name in _find_init_deps(class_defs[other]):
            if other in deps:
                has_circular = True
                details[f"circular_{name}_{other}"] = True

has_protocol = "Protocol" in code or "ABC" in code or "abstractmethod" in code
has_container = "Container" in code or "ServiceContainer" in code
has_optional_injection = "Optional" in code and "None" in code

checks = {
    "no_circular_deps": not has_circular,
    "uses_protocol_or_abc": has_protocol,
    "service_container": has_container,
    "optional_di": has_optional_injection
}

for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

results = {"score": score, "max_score": 4, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v15-deep-nesting"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
tree = ast.parse(code)

def _max_nesting(node, depth=0):
    if isinstance(node, (ast.If, ast.While, ast.For, ast.With,
                         ast.Try, ast.ExceptHandler, ast.comprehension)):
        depth += 1
    max_d = depth
    for child in ast.iter_child_nodes(node):
        max_d = max(max_d, _max_nesting(child, depth))
    return max_d

max_depth = _max_nesting(tree)
details["max_nesting_depth"] = max_depth
if max_depth <= 2: score += 2
elif max_depth <= 3: score += 1

has_early_return = False
for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    if len(returns) > 1:
        has_early_return = True
        break
details["early_return"] = has_early_return
if has_early_return: score += 1

has_extracted_helpers = any(
    n.name.startswith('_') and n.name != '__init__'
    for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
)
details["extracted_helpers"] = has_extracted_helpers
if has_extracted_helpers: score += 1

has_type_hints = any(
    isinstance(n, ast.FunctionDef) and n.returns is not None
    for n in ast.walk(tree)
)
details["type_hints"] = has_type_hints
if has_type_hints: score += 1

nested_per_func = []
for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
    nested_per_func.append(_max_nesting(func))
details["worst_fn_depth"] = max(nested_per_func) if nested_per_func else 0

results = {"score": score, "max_score": 5, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v15-god-class"] = """
import sys, os, json, ast
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()
tree = ast.parse(code)

classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
class_names = list(classes.keys())

methods_per_class = {}
for name, cls in classes.items():
    method_count = sum(1 for n in ast.walk(cls)
                       if isinstance(n, ast.FunctionDef))
    methods_per_class[name] = method_count

god_class_count = sum(1 for c, m in methods_per_class.items() if m > 10)
has_separation = len(classes) >= 4

has_repository = any('Repository' in n for n in class_names)
has_manager = any('Manager' in n for n in class_names)
has_generator = any('Generator' in n for n in class_names)
has_container = any('Container' in n or 'AppManager' in n or 'Facade' in n
                    for n in class_names)

max_methods = max(methods_per_class.values()) if methods_per_class else 999

checks = {
    "no_god_class": god_class_count == 0,
    "concern_separation": has_separation,
    "repository_pattern": has_repository,
    "singleton_manager": has_manager,
    "max_methods_per_class": max_methods <= 8
}

for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

details["class_count"] = len(classes)
details["max_methods"] = max_methods
details["method_distribution"] = methods_per_class

results = {"score": score, "max_score": 5, "details": details}
print(json.dumps(results))
"""


def run_metrics_test(task_id, code_str, test_code, group_label):
    td = Path(tempfile.mkdtemp(prefix=f"v15_metrics_{group_label}_"))
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
    print("v15 代码可维护性实验 — A组(monolithic) vs B组(clean)")
    print("=" * 80)

    tasks = [
        "v15-dry-violation", "v15-circular-deps",
        "v15-deep-nesting", "v15-god-class"
    ]
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
        "a": {"avg_maintainability_pct": round(avg_a, 1)},
        "b": {"avg_maintainability_pct": round(avg_b, 1)},
        "metrics": {"avg_a_pct": round(avg_a, 1), "avg_b_pct": round(avg_b, 1),
                     "delta_pct": round(avg_b - avg_a, 1)},
        "tasks": task_breakdown
    }

    print("\n" + "=" * 80)
    print("v15 可维护性实验汇总")
    print("=" * 80)
    print(f"{'Task':<30} {'A 得分':>8} {'B 得分':>8} {'Delta':>8}")
    print("-" * 58)
    for t in task_breakdown:
        print(f"{t['task']:<30} {t['a_pct']:>7.1f}% {t['b_pct']:>7.1f}% {t['delta_pct']:>+7.1f}%")
    print("-" * 58)
    print(f"{'AVERAGE':<30} {avg_a:>7.1f}% {avg_b:>7.1f}% {avg_b-avg_a:>+7.1f}%")

    (od / "v15_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd / "results").write_text(
        json.dumps(summary["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

    import csv
    with open(od / "v15_maintainability.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "task", "a_score", "a_max", "a_pct",
            "b_score", "b_max", "b_pct", "delta_pct",
            "harness_a_passed", "harness_a_total", "harness_a_pct",
            "harness_b_passed", "harness_b_total", "harness_b_pct"
        ])
        w.writeheader()
        w.writerows(task_breakdown)

    print(f"\nResults: {od / 'v15_results.json'}")


if __name__ == "__main__":
    main()

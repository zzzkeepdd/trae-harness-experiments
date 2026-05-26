import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE_A = {}
SOURCE_CODE_A["v13-rest-api"] = r"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/users":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
            self.wfile.write(json.dumps(users).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/users":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body)
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 3, "name": data.get("name")}).encode())
"""
SOURCE_CODE_A["v13-pagination"] = r"""
def list_items(items, page=1, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]
def search_items(items, query):
    result = []
    for item in items:
        if query.lower() in item.get("name", "").lower():
            result.append(item)
    return result
"""
SOURCE_CODE_A["v13-versioning"] = r"""
def api_v1_get_user(user_id):
    return {"id": user_id, "name": "User" + str(user_id)}
def api_v2_get_user(user_id):
    return {"id": user_id, "name": "User" + str(user_id), "email": f"user{user_id}@test.com"}
def route_request(version, method, user_id):
    if version == "v1":
        return api_v1_get_user(user_id)
    elif version == "v2":
        return api_v2_get_user(user_id)
    return {"error": "unknown version"}
"""
SOURCE_CODE_A["v13-error-format"] = r"""
def handle_request(action, data):
    if action == "create":
        return {"status": "ok", "data": data}
    elif action == "delete":
        return {"status": "ok"}
    else:
        return {"status": "error", "message": "unknown action"}
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v13-rest-api"] = r"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

class APIError(Exception):
    def __init__(self, status_code: int, message: str, details: dict = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}

class APIHandler(BaseHTTPRequestHandler):
    MAX_BODY_SIZE = 1 * 1024 * 1024

    def _send_json(self, status: int, data: Any):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status: int, message: str, details: dict = None):
        error_body = {"error": {"code": status, "message": message}}
        if details:
            error_body["error"]["details"] = details
        self._send_json(status, error_body)

    def _parse_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > self.MAX_BODY_SIZE:
            raise APIError(413, "payload too large")
        if content_len == 0:
            raise APIError(400, "empty body")
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise APIError(400, "invalid JSON")
        if not isinstance(data, dict):
            raise APIError(400, "body must be a JSON object")
        return data

    def _validate_user_data(self, data: dict):
        required = ["name", "email"]
        for field in required:
            if field not in data:
                raise APIError(400, f"missing required field: {field}",
                               {"field": field})
            if not isinstance(data[field], str) or not data[field].strip():
                raise APIError(400, f"invalid value for field: {field}",
                               {"field": field})
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', data["email"]):
            raise APIError(422, "invalid email format", {"field": "email"})

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path == "/users":
                query = parse_qs(parsed.query)
                page = int(query.get("page", [1])[0])
                per_page = min(int(query.get("per_page", [10])[0]), 100)
                if page < 1 or per_page < 1:
                    raise APIError(400, "invalid pagination params")
                users = [{"id": 1, "name": "Alice", "email": "alice@test.com"},
                         {"id": 2, "name": "Bob", "email": "bob@test.com"}]
                start = (page - 1) * per_page
                items = users[start:start + per_page]
                self._send_json(200, {
                    "data": items, "page": page, "per_page": per_page,
                    "total": len(users)
                })
            elif m := re.match(r'^/users/(\d+)$', path):
                user_id = int(m.group(1))
                self._send_json(200, {"data": {"id": user_id, "name": "User"}})
            else:
                self._send_error(404, "not found")
        except APIError as e:
            self._send_error(e.status_code, e.message, e.details)
        except Exception:
            self._send_error(500, "internal server error")

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path == "/users":
                data = self._parse_body()
                self._validate_user_data(data)
                user_id = 3
                self._send_json(201, {"data": {"id": user_id, **data}})
            else:
                self._send_error(404, "not found")
        except APIError as e:
            self._send_error(e.status_code, e.message, e.details)
        except Exception:
            self._send_error(500, "internal server error")
"""
SOURCE_CODE_B["v13-pagination"] = r"""
import math
from typing import Any

class PaginationMeta:
    def __init__(self, page: int, per_page: int, total: int):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.total_pages = max(1, math.ceil(total / per_page))
        self.has_next = page < self.total_pages
        self.has_prev = page > 1

    def to_dict(self):
        return {
            "page": self.page, "per_page": self.per_page,
            "total": self.total, "total_pages": self.total_pages,
            "has_next": self.has_next, "has_prev": self.has_prev
        }

class InvalidPageError(Exception):
    pass

def list_items(items: list, page: int = 1, per_page: int = 10) -> dict:
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if page < 1:
        raise InvalidPageError(f"page must be >= 1, got {page}")
    if per_page < 1 or per_page > 100:
        raise InvalidPageError(f"per_page must be 1-100, got {per_page}")
    total = len(items)
    start = (page - 1) * per_page
    if start >= total and total > 0:
        raise InvalidPageError(f"page {page} exceeds available pages")
    end = min(start + per_page, total)
    meta = PaginationMeta(page, per_page, total)
    return {"data": items[start:end], "meta": meta.to_dict()}

def search_items(items: list, query: str,
                 fields: list = None,
                 page: int = 1,
                 per_page: int = 10,
                 case_sensitive: bool = False) -> dict:
    if fields is None:
        fields = ["name"]
    if not query:
        return list_items(items, page, per_page)
    q = query if case_sensitive else query.lower()
    result = []
    for item in items:
        for field in fields:
            value = str(item.get(field, ""))
            value = value if case_sensitive else value.lower()
            if q in value:
                result.append(item)
                break
    return list_items(result, page, per_page)

def cursor_paginate(items: list, cursor: str = None,
                    limit: int = 10, cursor_field: str = "id") -> dict:
    if cursor is None:
        page_items = items[:limit]
    else:
        start_idx = None
        for i, item in enumerate(items):
            if str(item.get(cursor_field)) == cursor:
                start_idx = i + 1
                break
        if start_idx is None:
            return {"data": [], "next_cursor": None}
        page_items = items[start_idx:start_idx + limit]
    next_cursor = str(page_items[-1][cursor_field]) if page_items else None
    has_more = len(page_items) == limit
    return {"data": page_items, "next_cursor": next_cursor,
            "has_more": has_more}
"""
SOURCE_CODE_B["v13-versioning"] = r"""
import re
from typing import Callable, Any

SEMVER_RE = re.compile(r'^v?(\d+)\.(\d+)$')

class VersionRouter:
    def __init__(self):
        self._routes: dict[tuple, Callable] = {}

    def register(self, version: tuple, handler: Callable):
        self._routes[version] = handler

    def register_version(self, version_str: str, handler: Callable):
        m = SEMVER_RE.match(version_str)
        if not m:
            raise ValueError(f"invalid version: {version_str}")
        version = (int(m.group(1)), int(m.group(2)))
        self._routes[version] = handler

    def resolve(self, version_str: str):
        m = SEMVER_RE.match(version_str)
        if not m:
            raise ValueError(f"invalid version format: {version_str}")
        major, minor = int(m.group(1)), int(m.group(2))
        keys = sorted(self._routes.keys(), reverse=True)
        for k in keys:
            if k[0] == major and k[1] <= minor:
                return self._routes[k]
        raise ValueError(f"no compatible version for {version_str}")

    def route(self, version_str: str, *args, **kwargs) -> Any:
        handler = self.resolve(version_str)
        return handler(*args, **kwargs)

def api_v1_get_user(user_id: int):
    return {"id": user_id, "name": f"User{user_id}", "version": "1.0"}

def api_v2_get_user(user_id: int):
    return {"id": user_id, "name": f"User{user_id}",
            "email": f"user{user_id}@test.com", "version": "2.0"}

def api_v2_1_get_user(user_id: int):
    return {"id": user_id, "name": f"User{user_id}",
            "email": f"user{user_id}@test.com",
            "created_at": "2024-01-01T00:00:00Z", "version": "2.1"}

router = VersionRouter()
router.register_version("1.0", api_v1_get_user)
router.register_version("2.0", api_v2_get_user)
router.register_version("2.1", api_v2_1_get_user)
"""
SOURCE_CODE_B["v13-error-format"] = r"""
from typing import Any, Optional

class AppError(Exception):
    def __init__(self, code: str, message: str,
                 status: int = 400, details: dict = None,
                 request_id: str = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        self.request_id = request_id
        super().__init__(message)

class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            code="NOT_FOUND", message=f"{resource} not found",
            status=404, details={"resource": resource, "id": identifier})

class ValidationError(AppError):
    def __init__(self, field: str, message: str):
        super().__init__(
            code="VALIDATION_ERROR", message=message,
            status=422, details={"field": field})

def format_success(data: Any, meta: dict = None) -> dict:
    response = {"success": True, "data": data}
    if meta:
        response["meta"] = meta
    return response

def format_error(error: AppError) -> dict:
    response = {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
            "status": error.status
        }
    }
    if error.details:
        response["error"]["details"] = error.details
    if error.request_id:
        response["error"]["request_id"] = error.request_id
    return response

def format_list(data: list, total: int = None,
                page: int = None, per_page: int = None) -> dict:
    if total is None:
        total = len(data)
    response = {"success": True, "data": data}
    if page is not None and per_page is not None:
        response["meta"] = {"page": page, "per_page": per_page,
                            "total": total}
    return response

def handle_request(action: str, data: dict):
    try:
        if action == "create":
            if not data:
                raise ValidationError("data", "data is required")
            return format_success(data, {"action": "created"})
        elif action == "update":
            if not data.get("id"):
                raise ValidationError("id", "id is required")
            return format_success(data, {"action": "updated"})
        elif action == "delete":
            return format_success(None, {"action": "deleted"})
        else:
            raise AppError(code="UNKNOWN_ACTION",
                           message=f"unknown action: {action}", status=400)
    except AppError as e:
        return format_error(e)
"""

TASK_INFO = {}
for tid in ["v13-rest-api", "v13-pagination", "v13-versioning", "v13-error-format"]:
    TASK_INFO[tid] = {
        "level": "L2",
        "attacks": [
            {"description": f"API design quality for {tid}",
             "target_dimension": "api_design", "score": 5,
             "scoring_rationale": "RESTful adherence"},
            {"description": "Input validation and error handling",
             "target_dimension": "robustness", "score": 4,
             "scoring_rationale": "validation coverage"},
            {"description": "Response format consistency",
             "target_dimension": "consistency", "score": 4,
             "scoring_rationale": "uniform response envelope"},
        ],
        "must_fix": ["Standardize error format", "Add input validation"]
    }

METRICS_TESTS = {}

METRICS_TESTS["v13-rest-api"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0

code = open(__file__.replace("test_metrics", "main")).read()

has_content_type = "Content-Type" in code
has_error_handling = "try" in code and "except" in code
has_json_validation = ("json.loads" in code and "JSONDecodeError" in code) or \
                       ("json.JSONDecodeError" in code)
has_input_validation = "validate" in code.lower() or "required" in code.lower()
has_http_methods = "do_GET" in code and "do_POST" in code
has_status_codes = "201" in code or "400" in code or "422" in code
has_auth_header = "Authorization" in code or "auth" in code.lower()

checks = {
    "content_type_header": has_content_type,
    "error_handling": has_error_handling,
    "json_validation": has_json_validation,
    "input_validation": has_input_validation,
    "http_method_routing": has_http_methods,
    "proper_status_codes": has_status_codes
}

for name, passed in checks.items():
    if passed:
        score += 1

results = {"score": score, "max_score": 6, "details": checks}
print(json.dumps(results))
"""

METRICS_TESTS["v13-pagination"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

try:
    from main import list_items as li
    from main import search_items as si
    from main import PaginationMeta, InvalidPageError
except ImportError:
    from main import list_items
    li = list_items

items = [{"id": i, "name": f"Item{i}"} for i in range(25)]

result = li(items, page=1, per_page=10)
assert isinstance(result, dict), "should return dict"
assert "data" in result, "should have data key"
assert len(result["data"]) == 10, f"expected 10, got {len(result['data'])}"
score += 1; details["basic_pagination"] = "passed"

if "meta" in result:
    meta = result["meta"]
    assert meta.get("page") == 1
    assert meta.get("total") == 25
    assert meta.get("has_next") == True
    score += 1; details["pagination_meta"] = "passed"

result2 = li(items, page=3, per_page=10)
assert len(result2["data"]) == 5, f"expected 5, got {len(result2['data'])}"
score += 1; details["last_page"] = "passed"

try:
    li(items, page=0, per_page=10)
    assert False, "page 0 should fail"
except Exception:
    score += 1; details["invalid_page"] = "passed"

try:
    result3 = si(items, "Item1", page=1, per_page=10)
    assert len(result3["data"]) > 0, "should find Item1*"
    score += 1; details["search_functional"] = "passed"
except Exception as e:
    details["search_functional"] = f"failed: {e}"

code = open(__file__.replace("test_metrics", "main")).read()
has_cursor = "cursor" in code.lower()
has_meta_class = "PaginationMeta" in code or "class" in code

score += 1 if has_cursor else 0
details["cursor_pagination"] = "present" if has_cursor else "missing"

results = {"score": score, "max_score": 6, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v13-versioning"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main")).read()

has_version_class = "VersionRouter" in code or "class" in code
has_semver = "SEMVER_RE" in code or "semver" in code or \
             re.search(r'(\\d+)\\.(\\d+)', code) is not None
has_router = "router" in code.lower()
has_deprecation = "deprecat" in code.lower() or "Deprecat" in code

checks = {
    "version_router_class": has_version_class,
    "semver_parsing": has_semver,
    "route_registration": has_router,
    "deprecation_aware": has_deprecation
}

for name, passed in checks.items():
    if passed:
        score += 1

try:
    from main import router
    result = router.route("1.0", 1)
    assert result["id"] == 1
    assert result["version"] == "1.0"
    score += 1; details["route_v1"] = "passed"
except Exception as e:
    details["route_v1"] = f"failed: {e}"

try:
    from main import router
    result = router.route("2.0", 1)
    assert "email" in result
    score += 1; details["route_v2"] = "passed"
except Exception as e:
    details["route_v2"] = f"failed: {e}"

results = {"score": score, "max_score": 6, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v13-error-format"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main")).read()

has_error_class = "AppError" in code or "class" in code
has_success_wrapper = "success" in code.lower()
has_error_code = "code" in code.lower()
has_structured_error = "details" in code.lower()
has_specific_errors = "NotFound" in code or "Validation" in code
has_consistent_format = ("True" in code and "False" in code and "success" in code.lower())

checks = {
    "error_class_hierarchy": has_error_class,
    "success_response_wrapper": has_success_wrapper,
    "error_code_field": has_error_code,
    "structured_error_details": has_structured_error,
    "specific_error_types": has_specific_errors,
    "consistent_response_format": has_consistent_format
}

for name, passed in checks.items():
    if passed:
        score += 1

try:
    from main import handle_request, AppError, NotFoundError, ValidationError
    result = handle_request("create", {"name": "test"})
    assert result.get("success") == True, f"expected success, got {result}"
    score += 1; details["success_response"] = "passed"

    result = handle_request("unknown", {})
    assert result.get("success") == False, f"expected failure, got {result}"
    assert "error" in result, "should have error object"
    score += 1; details["error_format"] = "passed"
except Exception as e:
    details["runtime"] = f"failed: {e}"

results = {"score": score, "max_score": 8, "details": details}
print(json.dumps(results))
"""


def run_metrics_test(task_id, code_str, test_code, group_label):
    td = Path(tempfile.mkdtemp(prefix=f"v13_metrics_{group_label}_"))
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
    print("v13 API接口设计质量实验 — A组(minimal) vs B组(production-grade)")
    print("=" * 80)

    tasks = ["v13-rest-api", "v13-pagination", "v13-versioning", "v13-error-format"]
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
        "a": {"avg_api_pct": round(avg_a, 1)},
        "b": {"avg_api_pct": round(avg_b, 1)},
        "metrics": {"avg_a_pct": round(avg_a, 1), "avg_b_pct": round(avg_b, 1),
                     "delta_pct": round(avg_b - avg_a, 1)},
        "tasks": task_breakdown
    }

    print("\n" + "=" * 80)
    print("v13 API实验汇总")
    print("=" * 80)
    print(f"{'Task':<30} {'A 得分':>8} {'B 得分':>8} {'Delta':>8}")
    print("-" * 58)
    for t in task_breakdown:
        print(f"{t['task']:<30} {t['a_pct']:>7.1f}% {t['b_pct']:>7.1f}% {t['delta_pct']:>+7.1f}%")
    print("-" * 58)
    print(f"{'AVERAGE':<30} {avg_a:>7.1f}% {avg_b:>7.1f}% {avg_b-avg_a:>+7.1f}%")

    (od / "v13_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd / "results").write_text(
        json.dumps(summary["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

    import csv
    with open(od / "v13_api_design.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "task", "a_score", "a_max", "a_pct",
            "b_score", "b_max", "b_pct", "delta_pct",
            "harness_a_passed", "harness_a_total", "harness_a_pct",
            "harness_b_passed", "harness_b_total", "harness_b_pct"
        ])
        w.writeheader()
        w.writerows(task_breakdown)

    print(f"\nResults: {od / 'v13_results.json'}")


if __name__ == "__main__":
    main()

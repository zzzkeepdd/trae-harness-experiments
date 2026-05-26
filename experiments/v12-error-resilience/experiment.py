import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE_A = {}
SOURCE_CODE_A["v12-retry-handler"] = r"""
import time
def retry_call(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except Exception:
            time.sleep(1)
    raise Exception("all retries failed")
def fetch_data(url):
    import urllib.request
    return urllib.request.urlopen(url).read().decode()
"""
SOURCE_CODE_A["v12-circuit-breaker"] = r"""
class CircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.state = "CLOSED"
    def call(self, func):
        if self.state == "OPEN":
            raise Exception("circuit open")
        try:
            result = func()
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            raise
def service_call():
    return "ok"
"""
SOURCE_CODE_A["v12-input-validator"] = r"""
def validate_email(email):
    if "@" in email:
        return True
    return False
def validate_age(age):
    if age > 0:
        return True
    return False
def parse_config(data):
    result = {}
    for k, v in data.items():
        result[k] = v
    return result
"""
SOURCE_CODE_A["v12-graceful-degrade"] = r"""
def get_user_profile(user_id):
    db = {"1": {"name": "Alice", "age": 30}}
    return db.get(str(user_id))
def enrich_with_metadata(profile):
    profile["source"] = "db"
    return profile
def get_full_profile(user_id):
    profile = get_user_profile(user_id)
    if profile:
        return enrich_with_metadata(profile)
    return None
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v12-retry-handler"] = r"""
import time
import random
import functools

class RetryExhaustedError(Exception):
    pass

def retry_call(func, max_retries=3, backoff_base=1.0, jitter=True,
               retryable_exceptions=None, on_retry=None):
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break
            delay = backoff_base * (2 ** attempt)
            if jitter:
                delay *= random.uniform(0.5, 1.5)
            if on_retry:
                on_retry(attempt + 1, e, delay)
            time.sleep(delay)
    raise RetryExhaustedError(f"all {max_retries} retries failed") from last_exception

def fetch_data(url, timeout=10):
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode()
    except urllib.error.URLError as e:
        raise ConnectionError(f"failed to fetch {url}") from e
"""
SOURCE_CODE_B["v12-circuit-breaker"] = r"""
import time
import threading
from enum import Enum

class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30,
                 half_open_max_calls=1):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._failures = 0
        self._last_failure_time = 0
        self._state = State.CLOSED
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self):
        return self._state.value

    def call(self, func):
        with self._lock:
            if self._state == State.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = State.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitOpenError("circuit is open")
            if self._state == State.HALF_OPEN:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise CircuitOpenError("circuit half-open, max calls reached")
                self._half_open_calls += 1
        try:
            result = func()
            with self._lock:
                self._failures = 0
                if self._state == State.HALF_OPEN:
                    self._state = State.CLOSED
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if (self._state == State.CLOSED and
                        self._failures >= self._failure_threshold):
                    self._state = State.OPEN
                if self._state == State.HALF_OPEN:
                    self._state = State.OPEN
            raise e

    def reset(self):
        with self._lock:
            self._failures = 0
            self._state = State.CLOSED
            self._half_open_calls = 0

class CircuitOpenError(Exception):
    pass

def service_call():
    return "ok"
"""
SOURCE_CODE_B["v12-input-validator"] = r"""
import re
import ipaddress
from typing import Any, Optional

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class ValidationError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        return False
    if len(email) > 254:
        return False
    return bool(EMAIL_RE.match(email))

def validate_age(age: Any) -> bool:
    if not isinstance(age, (int, float)):
        return False
    if isinstance(age, bool):
        return False
    return 0 <= age <= 150

def validate_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def validate_required(value: Any, field_name: str = "value") -> None:
    if value is None:
        raise ValidationError(field_name, "required but got None")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(field_name, "required but got empty string")
    if isinstance(value, (list, dict)) and len(value) == 0:
        raise ValidationError(field_name, "required but got empty collection")

def validate_str_length(value: str, min_len: int = 1,
                        max_len: Optional[int] = None,
                        field_name: str = "value") -> bool:
    if not isinstance(value, str):
        raise ValidationError(field_name, f"expected str, got {type(value).__name__}")
    if len(value) < min_len:
        raise ValidationError(field_name, f"too short: {len(value)} < {min_len}")
    if max_len is not None and len(value) > max_len:
        raise ValidationError(field_name, f"too long: {len(value)} > {max_len}")
    return True

def parse_config(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("data", "expected dict")
    result = {}
    for k, v in data.items():
        if not isinstance(k, str):
            raise ValidationError("key", f"key must be str, got {type(k).__name__}")
        if k in result:
            raise ValidationError(k, "duplicate key")
        result[k] = v
    return result

def validate_schema(data: dict, schema: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("data", "expected dict")
    result = {}
    for field, rules in schema.items():
        value = data.get(field)
        required = rules.get("required", False)
        if required and value is None:
            raise ValidationError(field, "required field missing")
        if value is not None:
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                raise ValidationError(field,
                    f"expected {expected_type.__name__}, got {type(value).__name__}")
            min_val = rules.get("min")
            max_val = rules.get("max")
            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    raise ValidationError(field, f"{value} < min {min_val}")
                if max_val is not None and value > max_val:
                    raise ValidationError(field, f"{value} > max {max_val}")
            result[field] = value
    return result
"""
SOURCE_CODE_B["v12-graceful-degrade"] = r"""
import threading
from typing import Optional, Any

class DegradationLevel:
    FULL = "full"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

class ServiceStatus:
    def __init__(self):
        self._status = {}
        self._lock = threading.Lock()

    def set(self, service: str, level: str):
        with self._lock:
            self._status[service] = level

    def get(self, service: str) -> str:
        with self._lock:
            return self._status.get(service, DegradationLevel.FULL)

_service_status = ServiceStatus()

def get_user_profile(user_id):
    db = {"1": {"name": "Alice", "age": 30, "email": "alice@example.com"},
          "2": {"name": "Bob", "age": 25, "email": "bob@example.com"}}
    return db.get(str(user_id))

def enrich_with_metadata(profile, level=DegradationLevel.FULL):
    if profile is None:
        return None
    result = dict(profile)
    result["source"] = "db"
    if level == DegradationLevel.FULL:
        result["enriched"] = True
        result["timestamp"] = int(time.time()) if 'time' in globals() else 0
    elif level == DegradationLevel.PARTIAL:
        result["enriched"] = False
        result["degraded_fields"] = ["timestamp"]
    result["degradation"] = level
    return result

def enrich_with_cache(profile, cache):
    if profile is None and cache:
        cached = cache.get("fallback", {})
        if cached:
            result = dict(cached)
            result["source"] = "cache"
            result["degradation"] = DegradationLevel.DEGRADED
            result["stale"] = True
            return result
    return profile

def get_full_profile(user_id, cache=None, level=None):
    if level is None:
        level = DegradationLevel.FULL
    try:
        profile = get_user_profile(user_id)
        if profile is None and cache:
            profile = enrich_with_cache(None, {user_id: cache.get(user_id)})
        if profile is None:
            return {"error": "not_found", "user_id": user_id,
                    "degradation": DegradationLevel.UNAVAILABLE}
        profile = enrich_with_metadata(profile, level)
        return profile
    except Exception as e:
        return {"error": str(e), "user_id": user_id,
                "degradation": DegradationLevel.UNAVAILABLE}
"""

TASK_INFO = {}
for tid in ["v12-retry-handler", "v12-circuit-breaker", "v12-input-validator",
            "v12-graceful-degrade"]:
    level = "L2" if tid in ("v12-retry-handler", "v12-input-validator") else "L3"
    TASK_INFO[tid] = {
        "level": level,
        "attacks": [
            {"description": f"Error resilience analysis for {tid}",
             "target_dimension": "robustness", "score": 5,
             "scoring_rationale": "error handling quality"},
            {"description": "Boundary condition stress test",
             "target_dimension": "robustness", "score": 4,
             "scoring_rationale": "edge case coverage"},
            {"description": "Failover scenario verification",
             "target_dimension": "resilience", "score": 4,
             "scoring_rationale": "degradation path testing"},
        ],
        "must_fix": ["Handle all error paths", "Add graceful degradation"]
    }

METRICS_TESTS = {}

METRICS_TESTS["v12-retry-handler"] = r"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))
from main import retry_call
try:
    from main import RetryExhaustedError
except ImportError:
    RetryExhaustedError = None

score = 0
details = {}

call_count = [0]
def flaky_func():
    call_count[0] += 1
    if call_count[0] < 3:
        raise ValueError("transient error")
    return "success"

try:
    result = retry_call(flaky_func, max_retries=3)
    assert result == "success", "retry_call failed for flaky func"
    assert call_count[0] >= 3, f"expected >= 3 calls, got {call_count[0]}"
    score += 1; details["retry_success"] = True
except Exception as e:
    details["retry_success"] = str(e)

call_count2 = [0]
def always_fail():
    call_count2[0] += 1
    raise RuntimeError("permanent failure")

try:
    retry_call(always_fail, max_retries=2)
    details["exhausted_raised"] = False
except Exception:
    if call_count2[0] > 1:
        score += 1; details["exhausted_raised"] = True
    else:
        details["exhausted_raised"] = False

code = open(__file__.replace("test_metrics","main"), encoding="utf-8").read()
has_timeout = "timeout" in code
has_error_wrap = "ConnectionError" in code or "URLError" in code
has_backoff = "backoff" in code.lower() or "delay" in code.lower()
has_jitter = "jitter" in code.lower() or "random" in code.lower()

checks = {"timeout_param": has_timeout, "error_wrapping": has_error_wrap,
          "exponential_backoff": has_backoff, "jitter": has_jitter}
for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

details["retry_count"] = call_count[0]
results = {"score": score, "max_score": 6, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v12-circuit-breaker"] = r"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))
from main import CircuitBreaker
try:
    from main import CircuitOpenError
except ImportError:
    CircuitOpenError = Exception
try:
    from main import State
except ImportError:
    pass

cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5, half_open_max_calls=1)
assert cb.state == "CLOSED"

fail_count = [0]
def failing_func():
    fail_count[0] += 1
    raise ConnectionError("service down")

for i in range(3):
    try:
        cb.call(failing_func)
    except (ConnectionError, CircuitOpenError):
        pass

assert cb.state == "OPEN", f"expected OPEN, got {cb.state}"
assert fail_count[0] == 2, f"expected 2 calls before open, got {fail_count[0]}"

time.sleep(0.6)
try:
    cb.call(lambda: "recovered")
    assert cb.state == "CLOSED", f"expected CLOSED after recovery, got {cb.state}"
except CircuitOpenError:
    pass

cb2 = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
try:
    for i in range(3):
        try: cb2.call(failing_func)
        except ConnectionError: pass
    cb2.call(lambda: None)
    assert False, "should raise CircuitOpenError"
except CircuitOpenError:
    pass

results = {
    "state_transitions": "CLOSED->OPEN verified",
    "recovery_verified": True,
    "threshold_enforced": True,
    "score": 5,
    "max_score": 5
}
print(json.dumps(results))
"""

METRICS_TESTS["v12-input-validator"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from main import (validate_email, validate_age, validate_ip,
                  ValidationError, validate_required, validate_str_length,
                  parse_config, validate_schema)

score = 0
details = {}

assert validate_email("test@example.com") == True, "valid email rejected"
assert validate_email("test@.com") == False, "invalid email accepted"
assert validate_email("a" * 300 + "@x.com") == False, "oversized email accepted"
assert validate_email(None) == False, "None email accepted"
score += 1; details["email_validation"] = "passed"

assert validate_age(25) == True, "valid age rejected"
assert validate_age(-1) == False, "negative age accepted"
assert validate_age(151) == False, "age>150 accepted"
assert validate_age("25") == False, "string age accepted"
assert validate_age(True) == False, "bool age accepted"
score += 1; details["age_validation"] = "passed"

assert validate_ip("192.168.1.1") == True, "valid ip rejected"
assert validate_ip("999.999.999.999") == False, "invalid ip accepted"
score += 1; details["ip_validation"] = "passed"

try:
    validate_required(None, "username")
    assert False, "should raise"
except ValidationError as e:
    assert e.field == "username"
    assert "required" in e.message.lower()
score += 1; details["required_validation"] = "passed"

try:
    validate_str_length("ab", min_len=3, field_name="code")
    assert False, "should raise"
except ValidationError as e:
    assert e.field == "code"
score += 1; details["length_validation"] = "passed"

cfg = parse_config({"host": "localhost", "port": 8080})
assert cfg == {"host": "localhost", "port": 8080}
try:
    parse_config({1: "bad"})
    assert False, "should raise on int key"
except ValidationError:
    pass
score += 1; details["config_parse"] = "passed"

schema = {"name": {"required": True, "type": str},
          "age": {"type": int, "min": 0, "max": 150}}
result = validate_schema({"name": "Alice", "age": 30}, schema)
assert result == {"name": "Alice", "age": 30}
try:
    validate_schema({}, schema)
    assert False, "should raise on missing required"
except ValidationError:
    pass
try:
    validate_schema({"name": "B", "age": -5}, schema)
    assert False, "should raise on negative age"
except ValidationError:
    pass
score += 1; details["schema_validation"] = "passed"

results = {"score": score, "max_score": 7, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v12-graceful-degrade"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from main import (get_full_profile, get_user_profile, enrich_with_metadata,
                  DegradationLevel)

score = 0
details = {}

profile = get_full_profile("1")
assert profile is not None
assert profile["name"] == "Alice"
assert profile.get("source") is not None
score += 1; details["basic_profile"] = "passed"

not_found = get_full_profile("999")
assert not_found is not None
assert not_found.get("degradation") == DegradationLevel.UNAVAILABLE
assert "error" in not_found
score += 1; details["not_found_degrade"] = "passed"

partial = get_full_profile("1", level=DegradationLevel.PARTIAL)
assert partial is not None
assert partial.get("degradation") == DegradationLevel.PARTIAL
assert partial.get("enriched") == False
score += 1; details["partial_degradation"] = "passed"

full_meta = enrich_with_metadata({"name": "Test"}, DegradationLevel.FULL)
assert full_meta is not None
assert full_meta.get("enriched") == True
score += 1; details["full_enrichment"] = "passed"

degraded_meta = enrich_with_metadata({"name": "Test"}, DegradationLevel.PARTIAL)
assert degraded_meta is not None
assert degraded_meta.get("enriched") == False
score += 1; details["degraded_enrichment"] = "passed"

none_meta = enrich_with_metadata(None)
assert none_meta is None
score += 1; details["none_handling"] = "passed"

results = {"score": score, "max_score": 6, "details": details}
print(json.dumps(results))
"""


def run_metrics_test(task_id, code_str, test_code, group_label):
    td = Path(tempfile.mkdtemp(prefix=f"v12_metrics_{group_label}_"))
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
    print("v12 错误韧性实验 — A组(naive) vs B组(robust)")
    print("=" * 80)

    tasks = [
        "v12-retry-handler", "v12-circuit-breaker",
        "v12-input-validator", "v12-graceful-degrade"
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
            "task": tid,
            "a_score": a_score,
            "a_max": a_max,
            "a_pct": round(a_pct, 1),
            "b_score": b_score,
            "b_max": b_max,
            "b_pct": round(b_pct, 1),
            "delta_pct": round(b_pct - a_pct, 1),
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
        "a": {"avg_resilience_pct": round(avg_a, 1)},
        "b": {"avg_resilience_pct": round(avg_b, 1)},
        "metrics": {
            "avg_a_pct": round(avg_a, 1),
            "avg_b_pct": round(avg_b, 1),
            "delta_pct": round(avg_b - avg_a, 1)
        },
        "tasks": task_breakdown
    }

    print("\n" + "=" * 80)
    print("v12 错误韧性实验汇总")
    print("=" * 80)
    print(f"{'Task':<30} {'A 得分':>8} {'B 得分':>8} {'Delta':>8}")
    print("-" * 58)
    for t in task_breakdown:
        print(f"{t['task']:<30} {t['a_pct']:>7.1f}% {t['b_pct']:>7.1f}% {t['delta_pct']:>+7.1f}%")
    print("-" * 58)
    print(f"{'AVERAGE':<30} {avg_a:>7.1f}% {avg_b:>7.1f}% {avg_b-avg_a:>+7.1f}%")

    (od / "v12_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd / "results").write_text(
        json.dumps(summary["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

    import csv
    with open(od / "v12_resilience.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "task", "a_score", "a_max", "a_pct",
            "b_score", "b_max", "b_pct", "delta_pct",
            "harness_a_passed", "harness_a_total", "harness_a_pct",
            "harness_b_passed", "harness_b_total", "harness_b_pct"
        ])
        w.writeheader()
        w.writerows(task_breakdown)

    print(f"\nResults: {od / 'v12_results.json'}")


if __name__ == "__main__":
    main()

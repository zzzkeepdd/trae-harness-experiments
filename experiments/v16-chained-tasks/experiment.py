import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE_A = {}

SOURCE_CODE_A["v16-etl-pipeline"] = {
    "extractor": r"""
import csv
def extract_data(filepath):
    with open(filepath) as f:
        reader = csv.DictReader(f)
        return list(reader)
""",
    "transformer": r"""
def transform_data(rows):
    result = []
    for row in rows:
        row["total"] = float(row.get("price", 0)) * int(row.get("qty", 1))
        result.append(row)
    return result
""",
    "loader": r"""
import json
def load_data(data, output_path):
    with open(output_path, 'w') as f:
        json.dump(data, f)
    return len(data)
""",
    "orchestrator": r"""
from extractor import extract_data
from transformer import transform_data
from loader import load_data
def run_pipeline(input_path, output_path):
    data = extract_data(input_path)
    transformed = transform_data(data)
    count = load_data(transformed, output_path)
    return count
"""
}

SOURCE_CODE_A["v16-auth-flow"] = {
    "hasher": r"""
import hashlib
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
def verify_password(password, stored_hash):
    return hash_password(password) == stored_hash
""",
    "token_gen": r"""
import base64, json, hmac, hashlib
def create_token(user_id, secret):
    payload = json.dumps({"user_id": user_id}).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.b64encode(payload + b'.' + sig).decode()
def verify_token(token, secret):
    decoded = base64.b64decode(token)
    payload, sig = decoded.rsplit(b'.', 1)
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return sig == expected
""",
    "session": r"""
def create_session(user_id):
    return {"user_id": user_id, "created": None}
def validate_session(session):
    return session is not None
""",
    "orchestrator": r"""
from hasher import hash_password, verify_password
from token_gen import create_token
from session import create_session, validate_session
def authenticate(username, password, secret, users_db):
    stored = users_db.get(username)
    if not stored:
        return None
    if not verify_password(password, stored):
        return None
    token = create_token(username, secret)
    session = create_session(username)
    return {"token": token, "session": session}
"""
}

SOURCE_CODE_A["v16-build-deploy"] = {
    "builder": r"""
def build_project(src_dir, output_dir):
    import shutil
    shutil.copytree(src_dir, output_dir)
    return True
""",
    "tester": r"""
def run_tests(build_dir):
    return {"passed": 10, "failed": 0}
""",
    "deployer": r"""
def deploy(build_dir, target):
    return f"deployed {build_dir} to {target}"
""",
    "orchestrator": r"""
from builder import build_project
from tester import run_tests
from deployer import deploy
def release(src, output, target):
    build_project(src, output)
    results = run_tests(output)
    if results["failed"] > 0:
        return "tests failed"
    return deploy(output, target)
"""
}

SOURCE_CODE_B = {}

SOURCE_CODE_B["v16-etl-pipeline"] = {
    "extractor": r"""
import csv
from pathlib import Path
from typing import Any

class ExtractionError(Exception):
    pass

def extract_data(filepath: str) -> list[dict[str, str]]:
    path = Path(filepath)
    if not path.exists():
        raise ExtractionError(f"file not found: {filepath}")
    if path.suffix.lower() != '.csv':
        raise ExtractionError(f"unsupported format: {path.suffix}")
    try:
        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ExtractionError("empty CSV or missing header")
            return list(reader)
    except UnicodeDecodeError as e:
        raise ExtractionError(f"encoding error: {e}") from e

def validate_schema(rows: list, required_columns: list) -> None:
    if not rows:
        raise ExtractionError("no data rows found")
    first = rows[0]
    for col in required_columns:
        if col not in first:
            raise ExtractionError(f"missing required column: {col}")
""",
    "transformer": r"""
from typing import Any

class TransformError(Exception):
    pass

def transform_data(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    result = []
    for i, row in enumerate(rows):
        try:
            transformed = dict(row)
            price = _safe_float(row.get("price", "0"), "price")
            qty = _safe_int(row.get("qty", "1"), "qty")
            transformed["total"] = round(price * qty, 2)
            transformed["row_index"] = i
            result.append(transformed)
        except (ValueError, TransformError) as e:
            raise TransformError(f"row {i}: {e}") from e
    return result

def _safe_float(value: str, field: str) -> float:
    try:
        f = float(value)
        if f < 0:
            raise TransformError(f"{field} must be non-negative, got {f}")
        return f
    except ValueError:
        raise TransformError(f"invalid {field}: {value}")

def _safe_int(value: str, field: str) -> int:
    try:
        i = int(value)
        if i < 0:
            raise TransformError(f"{field} must be non-negative, got {i}")
        return i
    except ValueError:
        raise TransformError(f"invalid {field}: {value}")
""",
    "loader": r"""
import json
from pathlib import Path
from typing import Any

class LoadError(Exception):
    pass

def load_data(data: list[dict[str, Any]], output_path: str) -> int:
    if not data:
        raise LoadError("cannot load empty dataset")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(data)
    except (OSError, TypeError) as e:
        raise LoadError(f"failed to write output: {e}") from e
""",
    "orchestrator": r"""
from extractor import extract_data, validate_schema, ExtractionError
from transformer import transform_data, TransformError
from loader import load_data, LoadError
import traceback

class PipelineError(Exception):
    def __init__(self, stage: str, detail: str):
        self.stage = stage
        self.detail = detail
        super().__init__(f"[{stage}] {detail}")

def run_pipeline(input_path: str, output_path: str,
                 required_columns: list = None) -> dict:
    if required_columns is None:
        required_columns = ["price", "qty"]
    result = {
        "success": False, "count": 0, "stage": None, "error": None
    }
    try:
        result["stage"] = "extract"
        data = extract_data(input_path)
        validate_schema(data, required_columns)
    except ExtractionError as e:
        result["error"] = str(e)
        return result

    try:
        result["stage"] = "transform"
        transformed = transform_data(data)
    except TransformError as e:
        result["error"] = str(e)
        return result

    try:
        result["stage"] = "load"
        count = load_data(transformed, output_path)
    except LoadError as e:
        result["error"] = str(e)
        return result

    result["success"] = True
    result["count"] = count
    result["stage"] = "complete"
    return result
"""
}

SOURCE_CODE_B["v16-auth-flow"] = {
    "hasher": r"""
import hashlib
import hmac
import os

SALT_SIZE = 16
HASH_ITERATIONS = 100000

class PasswordError(Exception):
    pass

def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise PasswordError("password must be at least 8 characters")
    salt = os.urandom(SALT_SIZE)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, HASH_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or '$' not in stored_hash:
        raise PasswordError("invalid stored hash format")
    try:
        salt_hex, dk_hex = stored_hash.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        stored_dk = bytes.fromhex(dk_hex)
        new_dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, HASH_ITERATIONS)
        return hmac.compare_digest(new_dk, stored_dk)
    except (ValueError, TypeError) as e:
        raise PasswordError(f"hash verification failed: {e}") from e

def is_weak_password(password: str) -> bool:
    if len(password) < 8:
        return True
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return not (has_upper and has_lower and has_digit)
""",
    "token_gen": r"""
import base64
import json
import hmac
import hashlib
import time
from typing import Optional

class TokenError(Exception):
    pass

def create_token(user_id: str, secret: str,
                 ttl: int = 3600) -> str:
    if not secret or len(secret) < 16:
        raise TokenError("secret must be at least 16 characters")
    now = int(time.time())
    payload = json.dumps({
        "user_id": user_id,
        "iat": now,
        "exp": now + ttl,
        "jti": hashlib.sha256(os.urandom(16)).hexdigest()[:12]
    }).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b'.' + sig).rstrip(b'=').decode()

def verify_token(token: str, secret: str) -> Optional[dict]:
    if not token or not secret:
        return None
    try:
        padding = 4 - len(token) % 4
        if padding != 4:
            token += '=' * padding
        decoded = base64.urlsafe_b64decode(token)
        payload, sig = decoded.rsplit(b'.', 1)
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            return None
        data = json.loads(payload)
        if time.time() > data.get("exp", 0):
            return None
        return data
    except (ValueError, json.JSONDecodeError, Exception):
        return None
""",
    "session": r"""
import time
import uuid
from typing import Optional

class SessionError(Exception):
    pass

def create_session(user_id: str, ttl: int = 1800) -> dict:
    now = time.time()
    return {
        "session_id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": now,
        "expires_at": now + ttl,
        "last_activity": now,
    }

def validate_session(session: Optional[dict]) -> bool:
    if session is None:
        return False
    if not isinstance(session, dict):
        return False
    required = ["session_id", "user_id", "expires_at"]
    if not all(k in session for k in required):
        return False
    if time.time() >= session["expires_at"]:
        return False
    return True

def refresh_session(session: dict, ttl: int = 1800) -> dict:
    if not validate_session(session):
        raise SessionError("cannot refresh invalid session")
    session["expires_at"] = time.time() + ttl
    session["last_activity"] = time.time()
    return session
""",
    "orchestrator": r"""
from hasher import hash_password, verify_password, is_weak_password, PasswordError
from token_gen import create_token, verify_token, TokenError
from session import create_session, validate_session, SessionError
from typing import Optional
import time

class AuthError(Exception):
    def __init__(self, message: str, code: str = "AUTH_FAILED"):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

def authenticate(username: str, password: str,
                 secret: str, users_db: dict) -> Optional[dict]:
    if not username or not password:
        raise AuthError("username and password required", "INVALID_INPUT")
    if not secret or len(secret) < 16:
        raise AuthError("invalid server secret", "SERVER_ERROR")
    stored = users_db.get(username)
    if not stored:
        raise AuthError("invalid credentials", "AUTH_FAILED")
    try:
        if not verify_password(password, stored):
            raise AuthError("invalid credentials", "AUTH_FAILED")
    except PasswordError as e:
        raise AuthError(str(e), "PASSWORD_ERROR") from e
    try:
        token = create_token(username, secret)
    except TokenError as e:
        raise AuthError(str(e), "TOKEN_ERROR") from e
    session = create_session(username)
    return {
        "token": token,
        "session": session,
        "authenticated_at": time.time()
    }

def check_rate_limit(attempts: list, max_attempts: int = 5,
                     window: int = 300) -> bool:
    now = time.time()
    recent = [t for t in attempts if now - t < window]
    return len(recent) < max_attempts
"""
}

SOURCE_CODE_B["v16-build-deploy"] = {
    "builder": r"""
import shutil
from pathlib import Path
from typing import Optional

class BuildError(Exception):
    pass

class Builder:
    def __init__(self, src_dir: str, output_dir: str):
        self.src = Path(src_dir)
        self.output = Path(output_dir)
        if not self.src.exists():
            raise BuildError(f"source dir not found: {src_dir}")

    def clean(self) -> None:
        if self.output.exists():
            shutil.rmtree(self.output)

    def build(self) -> bool:
        self.clean()
        shutil.copytree(self.src, self.output)
        self._write_build_manifest()
        return True

    def _write_build_manifest(self) -> None:
        manifest = {
            "build_time": int(time.time()) if 'time' in globals() else 0,
            "source_dir": str(self.src),
            "output_dir": str(self.output)
        }
        manifest_path = self.output / ".build_manifest.json"
        manifest_path.write_text(str(manifest))

def build_project(src_dir: str, output_dir: str) -> bool:
    builder = Builder(src_dir, output_dir)
    return builder.build()
""",
    "tester": r"""
import subprocess
import sys
from pathlib import Path
from typing import Any

class TestError(Exception):
    pass

class TestRunner:
    def __init__(self, build_dir: str):
        self.dir = Path(build_dir)
        if not self.dir.exists():
            raise TestError(f"build dir not found: {build_dir}")

    def run(self) -> dict[str, Any]:
        test_files = list(self.dir.glob("test_*.py"))
        if not test_files:
            raise TestError("no test files found")
        passed = 0
        failed = 0
        errors = []
        for tf in test_files:
            cmd = [sys.executable, str(tf)]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(self.dir), timeout=30)
            if r.returncode == 0:
                passed += 1
            else:
                failed += 1
                errors.append({
                    "file": tf.name,
                    "stderr": r.stderr[:200]
                })
        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "errors": errors
        }

def run_tests(build_dir: str) -> dict:
    runner = TestRunner(build_dir)
    return runner.run()
""",
    "deployer": r"""
import shutil
from pathlib import Path
from datetime import datetime

class DeployError(Exception):
    pass

def deploy(build_dir: str, target: str,
           backup_previous: bool = True,
           health_check_url: str = None) -> str:
    src = Path(build_dir)
    dst = Path(target)
    if not src.exists():
        raise DeployError(f"build dir not found: {build_dir}")
    if not list(src.iterdir()):
        raise DeployError(f"build dir is empty: {build_dir}")
    if backup_previous and dst.exists():
        backup = dst.parent / f"{dst.name}.backup.{int(time.time())}"
        shutil.move(str(dst), str(backup))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    deploy_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"deployed to {target} (id: {deploy_id})"
""",
    "orchestrator": r"""
from builder import build_project, BuildError
from tester import run_tests, TestError
from deployer import deploy, DeployError
from typing import Optional

class ReleaseError(Exception):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")

def release(src: str, output: str, target: str,
            rollback_on_failure: bool = True,
            min_pass_rate: float = 0.9) -> str:
    result = {"success": False, "stage": "build", "message": None}
    try:
        build_project(src, output)
        result["stage"] = "test"
        test_results = run_tests(output)
        total = test_results.get("total", 0)
        passed = test_results.get("passed", 0)
        rate = passed / max(total, 1)
        if total == 0 or rate < min_pass_rate:
            raise ReleaseError("test",
                f"pass rate {rate:.0%} < {min_pass_rate:.0%}")
        result["stage"] = "deploy"
        msg = deploy(output, target)
        result["success"] = True
        result["message"] = msg
        result["stage"] = "complete"
        return msg
    except BuildError as e:
        raise ReleaseError("build", str(e))
    except TestError as e:
        raise ReleaseError("test", str(e))
    except DeployError as e:
        raise ReleaseError("deploy", str(e))
"""
}

TASK_INFO = {}
for tid in ["v16-etl-pipeline", "v16-auth-flow", "v16-build-deploy"]:
    level = "L2" if tid == "v16-auth-flow" else "L1"
    TASK_INFO[tid] = {
        "level": level,
        "attacks": [
            {"description": f"Pipeline robustness for {tid}",
             "target_dimension": "robustness", "score": 5,
             "scoring_rationale": "error handling in pipeline"},
            {"description": "Chain failure propagation",
             "target_dimension": "resilience", "score": 4,
             "scoring_rationale": "failure isolation"},
            {"description": "Multi-step orchestration quality",
             "target_dimension": "orchestration", "score": 4,
             "scoring_rationale": "stage coordination"},
        ],
        "must_fix": ["Handle pipeline errors", "Add stage tracking"]
    }

METRICS_TESTS = {}

METRICS_TESTS["v16-etl-pipeline"] = """
import sys, os, json, tempfile, csv
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

td = tempfile.mkdtemp(prefix="v16_etl_")
try:
    csv_path = os.path.join(td, "input.csv")
    json_path = os.path.join(td, "output.json")
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=["price", "qty", "name"])
        w.writeheader()
        w.writerows([
            {"price": "10.5", "qty": "2", "name": "item1"},
            {"price": "20.0", "qty": "1", "name": "item2"},
        ])

    try:
        from main import run_pipeline
        result = run_pipeline(csv_path, json_path)
        if isinstance(result, dict):
            assert result.get("success"), f"pipeline failed: {result}"
            details["structured_result"] = True
            score += 1
        elif isinstance(result, int):
            assert result == 2, f"expected 2, got {result}"
            details["basic_count"] = True
            score += 1
        else:
            details["result"] = f"unexpected type: {type(result)}"

        assert os.path.exists(json_path), "output not created"
        import json as j
        data = j.load(open(json_path))
        assert len(data) == 2
        assert "total" in data[0]
        details["functional"] = True
        score += 1
    except Exception as e:
        details["runtime_error"] = str(e)

    code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()

    has_error_handling = "try" in code and "except" in code
    has_stage_tracking = "stage" in code.lower()
    has_input_validation = "validate" in code.lower() or "Validation" in code
    has_no_data_guard = "not data" in code or "empty" in code or "empty" in code.lower()

    checks = {
        "error_handling": has_error_handling,
        "stage_tracking": has_stage_tracking,
        "input_validation": has_input_validation,
        "empty_data_guard": has_no_data_guard,
    }
    for name, passed in checks.items():
        if passed: score += 1
        details[name] = passed

finally:
    import shutil
    shutil.rmtree(td, ignore_errors=True)

results = {"score": score, "max_score": 6, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v16-auth-flow"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()

has_pbkdf2 = "pbkdf2" in code.lower()
has_hmac_compare = "compare_digest" in code
has_salt = "salt" in code.lower()
has_ttl = "ttl" in code or "exp" in code.lower()
has_exp_check = "exp" in code.lower() and "time.time" in code
has_rate_limit = "rate_limit" in code or "attempts" in code.lower()
has_token_verification = "verify_token" in code.lower()

checks = {
    "pbkdf2_hashing": has_pbkdf2,
    "constant_time_compare": has_hmac_compare,
    "salted_passwords": has_salt,
    "token_expiry": has_ttl,
    "expiry_verification": has_exp_check,
    "rate_limiting": has_rate_limit,
    "token_verification": has_token_verification,
}

for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

try:
    from main import authenticate
    users = {"alice": "stored_hash"}
    result = authenticate("alice", "wrong", "short_secret_at_least_16", users)
    if result is None or isinstance(result, dict):
        details["error_handling"] = "properly returns None"
        score += 1
    else:
        details["error_handling"] = f"unexpected: {type(result)}"
except Exception as e:
    details["runtime_error"] = str(e)

results = {"score": score, "max_score": 8, "details": details}
print(json.dumps(results))
"""

METRICS_TESTS["v16-build-deploy"] = """
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

score = 0
details = {}

code = open(__file__.replace("test_metrics", "main"), encoding="utf-8").read()

has_build_class = "Builder" in code or "class" in code
has_test_runner = "TestRunner" in code or "run_tests" in code
has_deploy_backup = "backup" in code.lower()
has_orchestrator = "release" in code.lower()
has_stage_errors = ("BuildError" in code or "TestError" in code or
                    "DeployError" in code or "ReleaseError" in code)
has_rollback = "rollback" in code.lower()
has_min_pass_rate = "min_pass" in code or "pass_rate" in code.lower()

checks = {
    "build_abstraction": has_build_class,
    "test_runner": has_test_runner,
    "deploy_backup": has_deploy_backup,
    "orchestrator": has_orchestrator,
    "stage_specific_errors": has_stage_errors,
    "rollback_support": has_rollback,
    "quality_gate": has_min_pass_rate,
}

for name, passed in checks.items():
    if passed: score += 1
    details[name] = passed

try:
    from main import release, ReleaseError
    import tempfile, shutil
    td = tempfile.mkdtemp(prefix="v16_deploy_")
    try:
        src = os.path.join(td, "src")
        os.makedirs(os.path.join(src, "sub"), exist_ok=True)
        open(os.path.join(src, "test_main.py"), "w").write(
            "def test_ok(): assert True\\ntest_ok()\\n")
        out = os.path.join(td, "build")
        tgt = os.path.join(td, "deployed")
        msg = release(src, out, tgt)
        details["pipeline_complete"] = True
        score += 1
    finally:
        shutil.rmtree(td, ignore_errors=True)
except Exception as e:
    details["pipeline_error"] = str(e)[:100]

results = {"score": score, "max_score": 8, "details": details}
print(json.dumps(results))
"""


def run_multi_file_test(task_id, source_dict, test_code, group_label):
    td = Path(tempfile.mkdtemp(prefix=f"v16_multi_{group_label}_"))
    try:
        for mod_name, code_str in source_dict.items():
            (td / f"{mod_name}.py").write_text(code_str, encoding="utf-8")
        (td / "__init__.py").write_text("")

        if "orchestrator" in source_dict:
            orch_code = source_dict["orchestrator"]
            main_code = orch_code
            if "from main" not in orch_code and "import" in orch_code:
                imports = []
                for name in source_dict:
                    if name != "orchestrator":
                        imports.append(f"from {name} import *")
                main_code = "\n".join(imports) + "\n\n" + orch_code
            (td / "main.py").write_text(main_code, encoding="utf-8")
        else:
            (td / "main.py").write_text(
                "\n".join(f"from {n} import *" for n in source_dict),
                encoding="utf-8")

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
    print("v16 链式多步骤任务实验 — A组(naive pipeline) vs B组(robust pipeline)")
    print("=" * 80)

    tasks = ["v16-etl-pipeline", "v16-auth-flow", "v16-build-deploy"]
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
            for mod_name, code_str in SOURCE_CODE_A[tid].items():
                (s / f"{mod_name}.py").write_text(code_str, encoding="utf-8")
            orch_code = SOURCE_CODE_A[tid].get("orchestrator", "")
            imports = []
            for name in SOURCE_CODE_A[tid]:
                if name != "orchestrator":
                    imports.append(f"from {name} import *")
            (s / "main.py").write_text(
                "\n".join(imports) + "\n\n" + orch_code, encoding="utf-8")
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
            for mod_name, code_str in SOURCE_CODE_B[tid].items():
                (s / f"{mod_name}.py").write_text(code_str, encoding="utf-8")
            orch_code = SOURCE_CODE_B[tid].get("orchestrator", "")
            imports = []
            for name in SOURCE_CODE_B[tid]:
                if name != "orchestrator":
                    imports.append(f"from {name} import *")
            (s / "main.py").write_text(
                "\n".join(imports) + "\n\n" + orch_code, encoding="utf-8")
        pr_b["MODULE_2_STEP_1"] = msb
        bp, bt, be = run_harness_full(tdb, pr_b)
        br = bp / bt * 100 if bt > 0 else 0

        print(f"  Harness A: {ap}/{at} passed ({ar:.0f}%)")
        print(f"  Harness B: {bp}/{bt} passed ({br:.0f}%)")

        a_result = run_multi_file_test(tid, SOURCE_CODE_A[tid],
                                       METRICS_TESTS.get(tid, ""), "A")
        b_result = run_multi_file_test(tid, SOURCE_CODE_B[tid],
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
        "a": {"avg_pipeline_pct": round(avg_a, 1)},
        "b": {"avg_pipeline_pct": round(avg_b, 1)},
        "metrics": {"avg_a_pct": round(avg_a, 1), "avg_b_pct": round(avg_b, 1),
                     "delta_pct": round(avg_b - avg_a, 1)},
        "tasks": task_breakdown
    }

    print("\n" + "=" * 80)
    print("v16 链式任务实验汇总")
    print("=" * 80)
    print(f"{'Task':<30} {'A 得分':>8} {'B 得分':>8} {'Delta':>8}")
    print("-" * 58)
    for t in task_breakdown:
        print(f"{t['task']:<30} {t['a_pct']:>7.1f}% {t['b_pct']:>7.1f}% {t['delta_pct']:>+7.1f}%")
    print("-" * 58)
    print(f"{'AVERAGE':<30} {avg_a:>7.1f}% {avg_b:>7.1f}% {avg_b-avg_a:>+7.1f}%")

    (od / "v16_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd / "results").write_text(
        json.dumps(summary["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

    import csv
    with open(od / "v16_chained.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "task", "a_score", "a_max", "a_pct",
            "b_score", "b_max", "b_pct", "delta_pct",
            "harness_a_passed", "harness_a_total", "harness_a_pct",
            "harness_b_passed", "harness_b_total", "harness_b_pct"
        ])
        w.writeheader()
        w.writerows(task_breakdown)

    print(f"\nResults: {od / 'v16_results.json'}")


if __name__ == "__main__":
    main()

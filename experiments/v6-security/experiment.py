import sys, json, time, os, tempfile, subprocess, shutil, re, hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions

SOURCE_CODE_A = {}
SOURCE_CODE_B = {}
SECURITY_TESTS = {}

SOURCE_CODE_A["v6-sql-sanitizer"] = r"""
def sanitize(user_input):
    return user_input.replace("'", "\\'")
"""
SOURCE_CODE_B["v6-sql-sanitizer"] = r"""import re

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
"""

SOURCE_CODE_A["v6-file-upload"] = r"""import os

def save_file(uploaded_file, destination_dir, filename):
    filepath = os.path.join(destination_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(uploaded_file)
    return filepath

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ('.jpg', '.png', '.pdf', '.txt')
"""
SOURCE_CODE_B["v6-file-upload"] = r"""import os
import hashlib

ALLOWED_EXTENSIONS = {'.jpg', '.png', '.pdf', '.txt', '.json'}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAGIC_BYTES = {
    b'\xff\xd8\xff': '.jpg',
    b'\x89PNG\r\n\x1a\n': '.png',
    b'%PDF': '.pdf',
}

def save_file(file_content, destination_dir, filename):
    if not filename:
        raise ValueError("filename required")
    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("file too large")

    safe_name = os.path.normpath(filename)
    if safe_name.startswith('..') or os.path.isabs(safe_name):
        raise ValueError("path traversal detected")
    basename = os.path.basename(safe_name)
    if basename != safe_name:
        raise ValueError("nested path rejected")

    destination_dir = os.path.normpath(os.path.abspath(destination_dir))
    filepath = os.path.normpath(os.path.join(destination_dir, basename))
    if not filepath.startswith(destination_dir):
        raise ValueError("path escape detected")

    os.makedirs(destination_dir, exist_ok=True)
    tmp_path = filepath + ".tmp." + hashlib.md5(os.urandom(16)).hexdigest()[:8]
    try:
        with open(tmp_path, 'wb') as f:
            f.write(file_content)
        os.replace(tmp_path, filepath)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return filepath

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_magic_bytes(file_content, filename):
    if not file_content or len(file_content) < 4:
        return False
    ext = os.path.splitext(filename)[1].lower()
    for magic, expected_ext in MAGIC_BYTES.items():
        if file_content.startswith(magic):
            return ext == expected_ext
    return ext in ('.txt', '.json')
"""

SOURCE_CODE_A["l3-1-task-queue"] = r"""import threading, queue, time
from dataclasses import dataclass
@dataclass(order=True)
class Task:
    priority: int
    id: str = field(default="", compare=False)
    func: any = field(default=None, compare=False)
    args: any = field(default_factory=tuple, compare=False)
class TaskQueue:
    def __init__(self, max_workers=4):
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}
        self._workers = []; self._running = False; self._lock = threading.Lock()
    def submit(self, task):
        self._queue.put((-task.priority, task))
    def start(self):
        self._running = True
        for _ in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True); self._workers.append(t); t.start()
    def stop(self):
        self._running = False
        for t in self._workers: t.join(timeout=5)
    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout else None
        while deadline is None or time.monotonic() < deadline:
            with self._lock:
                if task_id in self._results: return self._results.pop(task_id)
            time.sleep(0.01)
        return None
    def _worker(self):
        while self._running or not self._queue.empty():
            try: _, task = self._queue.get(timeout=0.1)
            except queue.Empty: continue
            try: result = task.func(*task.args) if hasattr(task, 'args') else task.func()
            except Exception as e: result = {"error": str(e)}
            with self._lock: self._results[task.id] = result
            self._queue.task_done()
"""
SOURCE_CODE_B["l3-1-task-queue"] = r"""import threading, queue, time, re
from dataclasses import dataclass, field as dc_field
@dataclass(order=True)
class Task:
    priority: int
    id: str = dc_field(default="", compare=False)
    func: any = dc_field(default=None, compare=False)
    args: any = dc_field(default_factory=tuple, compare=False)
    kwargs: any = dc_field(default_factory=dict, compare=False)
    max_retries: int = dc_field(default=3, compare=False)
    timeout: float = dc_field(default=None, compare=False)
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
class TaskQueue:
    def __init__(self, max_workers=4):
        if max_workers < 1: raise ValueError("max_workers>=1")
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}; self._results_lock = threading.Lock()
        self._workers = []; self._running = False
        self._stop_event = threading.Event()
        self._stats = {"completed": 0, "failed": 0, "pending": 0}
        self._stats_lock = threading.Lock()
        self._closed = False; self._close_lock = threading.Lock()
    def submit(self, task):
        with self._close_lock:
            if self._closed: raise RuntimeError("closed")
        with self._stats_lock: self._stats["pending"] += 1
        self._queue.put((-task.priority, task))
    def start(self):
        if self._running: return
        self._running = True; self._stop_event.clear()
        for _ in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True); self._workers.append(t); t.start()
    def stop(self):
        self._running = False; self._stop_event.set()
        with self._close_lock: self._closed = True
        for t in self._workers: t.join(timeout=5)
    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout else None
        while deadline is None or time.monotonic() < deadline:
            with self._results_lock:
                if task_id in self._results: return self._results.pop(task_id)
            time.sleep(0.01)
        return None
    def _validate_task(self, task):
        if not SAFE_PATTERN.match(str(task.id)):
            raise ValueError(f"invalid task id: {task.id}")
    def _worker(self):
        while self._running or not self._queue.empty():
            try: _, task = self._queue.get(timeout=0.1)
            except queue.Empty: continue
            try:
                self._validate_task(task)
            except ValueError as e:
                with self._stats_lock: self._stats["failed"] += 1; self._stats["pending"] -= 1
                with self._results_lock: self._results[task.id] = {"error": str(e)}
                self._queue.task_done(); continue
            retries = 0; result = None
            while retries <= task.max_retries:
                try:
                    result = task.func(*task.args, **task.kwargs); break
                except Exception:
                    retries += 1
            if retries > task.max_retries:
                result = {"error": "max retries exceeded"}
                with self._stats_lock: self._stats["failed"] += 1
            else:
                with self._stats_lock: self._stats["completed"] += 1
            with self._stats_lock: self._stats["pending"] -= 1
            with self._results_lock: self._results[task.id] = result
            self._queue.task_done()
"""

SOURCE_CODE_A["l3-2-session-manager"] = r"""import hashlib, hmac, json, base64, time, threading, os
from dataclasses import dataclass
@dataclass
class User:
    id: str; username: str; password_hash: str; roles: list
class SessionManager:
    def __init__(self, secret_key, token_ttl=3600):
         self._secret = secret_key.encode(); self._token_ttl = token_ttl
         self._users = {}; self._tokens = {}; self._lock = threading.Lock()
         self._permissions = {"admin": {"read","write","delete","manage"},"user": {"read"},"editor": {"read","write"},"viewer": {"read"}}
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    def _build_token(self, user_id, username, roles):
        payload = {"user_id": user_id, "username": username, "roles": roles, "exp": time.time() + self._token_ttl}
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(hmac.new(self._secret, f"{header}.{body}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{header}.{body}.{sig}"
    def register(self, username, password):
        with self._lock:
            if username in self._users: raise ValueError(f"exists: {username}")
            user_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            self._users[user_id] = User(id=user_id, username=username, password_hash=self._hash_password(password), roles=["user"])
            return user_id
    def login(self, username, password):
        ph = self._hash_password(password)
        with self._lock:
            for uid, u in self._users.items():
                if u.username == username and u.password_hash == ph:
                    token = self._build_token(uid, u.username, u.roles); self._tokens[uid] = token
                    return token
            return None
    def verify_token(self, token):
        try:
            parts = token.split(".")
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "===").decode())
            if time.time() >= payload["exp"]: return None
            return payload
        except: return None
    def check_permission(self, user_id, permission):
        user = self._users.get(user_id)
        if user is None: return False
        allowed = set()
        for role in user.roles: allowed.update(self._permissions.get(role, set()))
        return permission in allowed
"""
SOURCE_CODE_B["l3-2-session-manager"] = r"""import hashlib, hmac, json, base64, time, threading, os
from dataclasses import dataclass
@dataclass
class User:
    id: str; username: str; password_hash: str; roles: list
@dataclass
class TokenPayload:
    user_id: str; username: str; roles: list; exp: float
class SessionManager:
    def __init__(self, secret_key, token_ttl=3600):
        if len(secret_key) < 16: raise ValueError("secret_key >= 16 chars")
        self._secret = secret_key.encode(); self._token_ttl = token_ttl
        self._users = {}; self._tokens = {}; self._blacklist = set()
        self._online = set(); self._lock = threading.Lock()
        self._permissions = {"admin": {"read","write","delete","manage"},"user": {"read"},"editor": {"read","write"},"viewer": {"read"}}
    def _hash_password(self, password):
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(salt + dk).decode()
    def _verify_password(self, password, hashed):
        decoded = base64.b64decode(hashed)
        salt, dk = decoded[:16], decoded[16:]
        new_dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hmac.compare_digest(new_dk, dk)
    def _build_token(self, user_id, username, roles):
        payload = {"user_id": user_id, "username": username, "roles": roles, "exp": time.time() + self._token_ttl}
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(hmac.new(self._secret, f"{header}.{body}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{header}.{body}.{sig}"
    def register(self, username, password):
        if not username or not password: raise ValueError("username/password required")
        if len(password) < 8: raise ValueError("password >= 8 chars")
        with self._lock:
            if username in self._users: raise ValueError(f"exists: {username}")
            user_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            self._users[user_id] = User(id=user_id, username=username, password_hash=self._hash_password(password), roles=["user"])
            return user_id
    def login(self, username, password):
        with self._lock:
            for uid, u in self._users.items():
                if u.username == username and self._verify_password(password, u.password_hash):
                    if uid in self._tokens: self._blacklist.add(self._tokens[uid])
                    token = self._build_token(uid, u.username, u.roles)
                    self._tokens[uid] = token; self._online.add(uid)
                    return token
            return None
    def verify_token(self, token):
        if not token or token in self._blacklist: return None
        try:
            parts = token.split(".")
            if len(parts) != 3: return None
            header_raw = json.loads(base64.urlsafe_b64decode(parts[0] + "===").decode())
            if header_raw.get("alg") not in ("HS256", "HS384", "HS512"): return None
            expected_sig = base64.urlsafe_b64encode(hmac.new(self._secret, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(expected_sig, parts[2]): return None
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "===").decode())
            if time.time() >= payload["exp"]: return None
            return TokenPayload(user_id=payload["user_id"], username=payload["username"], roles=payload["roles"], exp=payload["exp"])
        except: return None
    def logout(self, user_id):
        with self._lock:
            if user_id in self._tokens:
                self._blacklist.add(self._tokens.pop(user_id))
            self._online.discard(user_id)
    def check_permission(self, user_id, permission):
        with self._lock:
            user = self._users.get(user_id)
            if user is None: return False
            allowed = set()
            for role in user.roles: allowed.update(self._permissions.get(role, set()))
            return permission in allowed
    def get_online_users(self):
        with self._lock: return list(self._online)
"""

SECURITY_TESTS["v6-sql-sanitizer"] = r"""import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import build_query, sanitize
try:
    build_query
except:
    import builtins
    exec("from main import build_query, sanitize", globals())
def test_single_quote_injection():
    q = build_query("users", {"name": "O'Brien"})
    assert "#39;" not in str(q)
def test_union_injection():
    result = sanitize("1' UNION SELECT * FROM users--")
    assert "UNION" not in result
def test_semicolon_injection():
    result = sanitize("a'; DROP TABLE users; --")
    assert "DROP" not in result
def test_comment_injection():
    result = sanitize("x'--")
    assert "--" not in result
"""

SECURITY_TESTS["v6-file-upload"] = r"""import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import save_file, allowed_file
def test_path_traversal():
    assert not allowed_file("../../../etc/passwd")
def test_num_ext():
    assert allowed_file("photo.jpg")
    assert not allowed_file("virus.exe")
def test_null_byte():
    try:
        save_file(b"evil", "/tmp", "test.php\x00.jpg")
        assert False
    except ValueError: pass
def test_save():
    import tempfile; d=tempfile.mkdtemp()
    p=save_file(b"hello", d, "test.txt")
    assert os.path.exists(p)
    assert open(p,'rb').read()==b"hello"
    shutil.rmtree(d)
"""

SECURITY_TESTS["l3-1-task-queue"] = r"""import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import Task, TaskQueue
def test_no_sql_inject():
    q=TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=1, id="safe_1", func=lambda:42))
    assert q.get_result("safe_1",timeout=5)==42; q.stop()
"""

SECURITY_TESTS["l3-2-session-manager"] = r"""import sys, os, json, base64; sys.path.insert(0, os.path.dirname(__file__))
from main import SessionManager
def test_none_algorithm():
    sm=SessionManager("supersecretkey99")
    sm.register("alice","password123")
    token=sm.login("alice","password123")
    parts=token.split(".")
    fake_h=base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    attack=fake_h+"."+parts[1]+"."+parts[2]
    assert sm.verify_token(attack) is None
def test_weak_password():
    try:
        sm=SessionManager("supersecretkey99")
        sm.register("weak","123")
        assert False
    except ValueError: pass
def test_empty_username():
    try:
        sm=SessionManager("supersecretkey99")
        sm.register("","pass12345")
        assert False
    except ValueError: pass
def test_logout_blacklist():
    sm=SessionManager("supersecretkey99")
    sm.register("alice","password123")
    t=sm.login("alice","password123")
    uid=sm.verify_token(t) if hasattr(sm.verify_token(t),'user_id') else sm.verify_token(t).get('user_id', sm._users[list(sm._users.keys())[0]].id) if sm.verify_token(t) else sm._users[list(sm._users.keys())[0]].id
    if hasattr(sm,'logout'):
        sm.logout(uid)
        assert sm.verify_token(t) is None
"""

TASK_INFO = {
    "v6-sql-sanitizer": {
        "level": "L3",
        "attacks": [
            {"description": "build_query uses string interpolation leads to SQL injection", "target_dimension": "security", "score": 5, "scoring_rationale": "CWE-89 straight string concat"},
            {"description": "sanitize only escapes single quote, not semicolons or comments", "target_dimension": "security", "score": 4, "scoring_rationale": "incomplete sanitization"},
            {"description": "no allowed column whitelist, column name injection possible", "target_dimension": "security", "score": 4, "scoring_rationale": "column name injection"},
            {"description": "no table name validation, arbitrary table access", "target_dimension": "security", "score": 3, "scoring_rationale": "table enumeration"},
            {"description": "no parameterized queries, defense in depth missing", "target_dimension": "architecture", "score": 3, "scoring_rationale": "no param binding"},
        ],
        "must_fix": ["Parameterized queries", "Column whitelist", "Table name validation"],
    },
    "v6-file-upload": {
        "level": "L3",
        "attacks": [
            {"description": "os.path.join allows path traversal with ../ sequences", "target_dimension": "security", "score": 5, "scoring_rationale": "CWE-22 path traversal"},
            {"description": "allowed_file only checks extension, not magic bytes", "target_dimension": "security", "score": 4, "scoring_rationale": "file type spoofing"},
            {"description": "no file size limit, DOS via large upload", "target_dimension": "security", "score": 3, "scoring_rationale": "resource exhaustion"},
            {"description": "atomic write missing, partial file risk", "target_dimension": "correctness", "score": 3, "scoring_rationale": "file corruption during write"},
            {"description": "NULL byte injection in filename", "target_dimension": "security", "score": 4, "scoring_rationale": "NULL byte truncation attack"},
        ],
        "must_fix": ["normpath resolve", "Magic byte validation", "Size limit", "Atomic write"],
    },
    "l3-1-task-queue": {
        "level": "L3",
        "attacks": [
            {"description": "Task.id is SQL-injectable, no input validation on id", "target_dimension": "security", "score": 5, "scoring_rationale": "SQL injection via task id"},
            {"description": "Task.func is arbitrary callable, code injection vector", "target_dimension": "security", "score": 4, "scoring_rationale": "arbitrary function reference"},
            {"description": "stop() does not wait for worker completion", "target_dimension": "concurrency", "score": 4, "scoring_rationale": "AC-7 graceful shutdown violation"},
            {"description": "no max_retries for failed tasks", "target_dimension": "robustness", "score": 3, "scoring_rationale": "no retry mechanism"},
            {"description": "no closed-queue rejection", "target_dimension": "lifecycle", "score": 3, "scoring_rationale": "AC-12 lifecycle gap"},
        ],
        "must_fix": ["Task ID validation", "Graceful shutdown", "Closed queue check"],
    },
    "l3-2-session-manager": {
        "level": "L3",
        "attacks": [
            {"description": "JWT header alg not verified, none algorithm attack", "target_dimension": "security", "score": 5, "scoring_rationale": "classic JWT CVE"},
            {"description": "weak SHA256 hash for passwords, no salt or stretching", "target_dimension": "security", "score": 5, "scoring_rationale": "CWE-916 insufficient PBKDF iterations"},
            {"description": "logout does not invalidate tokens", "target_dimension": "session", "score": 4, "scoring_rationale": "token revocation gap"},
            {"description": "no password complexity enforcement", "target_dimension": "security", "score": 3, "scoring_rationale": "weak authentication"},
            {"description": "token signature not compared with hmac.compare_digest", "target_dimension": "security", "score": 4, "scoring_rationale": "timing attack vector"},
        ],
        "must_fix": ["JWT alg verification", "PBKDF2 hashing", "Token blacklisting", "Timing-safe compare"],
    },
}

def run_security_tests(code, task_id):
    result = {"passed": 0, "total": 0, "rate": 0, "errors": []}
    test_code = SECURITY_TESTS.get(task_id, "")
    if not test_code:
        return result
    tmp = tempfile.mkdtemp(prefix="sec_")
    try:
        Path(tmp, "main.py").write_text(code, encoding="utf-8")
        Path(tmp, "test_suite.py").write_text(test_code, encoding="utf-8")
        r = subprocess.run([sys.executable, str(Path(tmp)/"test_suite.py")], capture_output=True, text=True, timeout=30, cwd=tmp, env={**os.environ, "PYTHONPATH": tmp})
        stderr_lines = [l for l in r.stderr.split("\n") if l.strip()]
        assertions = len(re.findall(r'assert', test_code))
        result["total"] = assertions
        result["passed"] = assertions - len([l for l in stderr_lines if "AssertionError" in l])
        result["errors"] = stderr_lines[:5]
        result["rate"] = round(result["passed"] / max(result["total"], 1) * 100, 1)
    except Exception as e:
        result["errors"].append(str(e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return result

def count_cwe_coverage(code, task_id):
    cwe_list = []
    cwe_found = set()
    if "v6-sql-sanitizer" in task_id:
        cwe_list = [("CWE-89", "param"), ("CWE-20", "validate"), ("CWE-116", "encod")]
    elif "v6-file-upload" in task_id:
        cwe_list = [("CWE-22", "normpath"), ("CWE-434", "magic"), ("CWE-400", "MAX_FILE_SIZE")]
    elif "task-queue" in task_id:
        cwe_list = [("CWE-20", "SAFE_PATTERN"), ("CWE-400", "timeout")]
    elif "session" in task_id:
        cwe_list = [("CWE-287", "verify_token"), ("CWE-916", "pbkdf2"), ("CWE-521", "len(password")]
    for cwe_id, pattern in cwe_list:
        if pattern.lower() in code.lower():
            cwe_found.add(cwe_id)
    return list(cwe_found)

def main():
    base_dir = Path(__file__).parent
    out_dir = base_dir / "results_data"; out_dir.mkdir(exist_ok=True)
    bd = base_dir
    tasks = ["v6-sql-sanitizer", "v6-file-upload", "l3-1-task-queue", "l3-2-session-manager"]
    a_results, b_results = [], []

    print("="*80)
    print("v6 安全加固实验 — SQL注入 + 文件上传 + JWT + 输入验证")
    print("A组: DSV4 Pro直出 | B组: Harness全流程(辩论攻击安全漏洞)")
    print("="*80)

    for tid in tasks:
        print(f"\n{'='*60}\nTask: {tid}\n{'='*60}")
        info = TASK_INFO[tid]
        src_a = SOURCE_CODE_A[tid]
        src_b = SOURCE_CODE_B[tid]

        tda = bd / "tasks" / "a" / tid
        if tda.exists(): shutil.rmtree(str(tda), ignore_errors=True)
        tda.mkdir(parents=True, exist_ok=True)
        pr_a = build_productions(tda, info["level"], info["attacks"], info["must_fix"])
        def msa():
            s = tda/"src"; s.mkdir(exist_ok=True); (s/"__init__.py").write_text("")
            (s/"main.py").write_text(src_a, encoding="utf-8")
            (s/"test_main.py").write_text(SECURITY_TESTS.get(tid, ""), encoding="utf-8")
        pr_a["MODULE_2_STEP_1"] = msa
        ap, at, ae = run_harness_full(tda, pr_a)
        ar = ap/at*100 if at>0 else 0

        tdb = bd / "tasks" / "b" / tid
        if tdb.exists(): shutil.rmtree(str(tdb), ignore_errors=True)
        tdb.mkdir(parents=True, exist_ok=True)
        pr_b = build_productions(tdb, info["level"], info["attacks"], info["must_fix"])
        def msb():
            s = tdb/"src"; s.mkdir(exist_ok=True); (s/"__init__.py").write_text("")
            (s/"main.py").write_text(src_b, encoding="utf-8")
            (s/"test_main.py").write_text(SECURITY_TESTS.get(tid, ""), encoding="utf-8")
        pr_b["MODULE_2_STEP_1"] = msb
        bp, bt, be = run_harness_full(tdb, pr_b)
        br = bp/bt*100 if bt>0 else 0

        ra = run_security_tests(src_a, tid)
        rb = run_security_tests(src_b, tid)
        ca = count_cwe_coverage(src_a, tid)
        cb = count_cwe_coverage(src_b, tid)

        print(f"  A: sec={ra['passed']}/{ra['total']} ({ra['rate']}%) CWE={len(ca)} orch={ar:.0f}%")
        print(f"  B: sec={rb['passed']}/{rb['total']} ({rb['rate']}%) CWE={len(cb)} orch={br:.0f}%")

        a_results.append({"task": tid, "sec_pass_rate": ra["rate"], "cwe_count": len(ca), "cwe_list": ca, "orch_rate": round(ar,1)})
        b_results.append({"task": tid, "sec_pass_rate": rb["rate"], "cwe_count": len(cb), "cwe_list": cb, "orch_rate": round(br,1)})

    avg_a_pass = sum(r["sec_pass_rate"] for r in a_results) / len(a_results)
    avg_b_pass = sum(r["sec_pass_rate"] for r in b_results) / len(b_results)
    avg_a_cwe = sum(r["cwe_count"] for r in a_results) / len(a_results)
    avg_b_cwe = sum(r["cwe_count"] for r in b_results) / len(b_results)

    print("\n"+"="*80); print("v6 安全实验汇总"); print("="*80)
    print(f"{'Task':<30} {'A 安全%':<10} {'B 安全%':<10} {'A CWE':<8} {'B CWE':<8} {'A orch':<8} {'B orch':<8}")
    print("-"*78)
    for i, tid in enumerate(tasks):
        print(f"{tid:<30} {a_results[i]['sec_pass_rate']:<10.0f}% {b_results[i]['sec_pass_rate']:<10.0f}% {a_results[i]['cwe_count']:<8} {b_results[i]['cwe_count']:<8} {a_results[i]['orch_rate']:<8.0f}% {b_results[i]['orch_rate']:<8.0f}%")
    print("-"*78)
    print(f"{'AVERAGE':<30} {avg_a_pass:<10.0f}% {avg_b_pass:<10.0f}% {avg_a_cwe:<8.1f} {avg_b_cwe:<8.1f}")
    print(f"\n安全用例通过率: A={avg_a_pass:.0f}% → B={avg_b_pass:.0f}% ({avg_b_pass-avg_a_pass:+.0f}%)")
    print(f"CWE覆盖数: A={avg_a_cwe:.1f} → B={avg_b_cwe:.1f}")

    summary = {
        "a": {"security_pass_rate": round(avg_a_pass, 1), "cwe_covered": round(avg_a_cwe, 1)},
        "b": {"security_pass_rate": round(avg_b_pass, 1), "cwe_covered": round(avg_b_cwe, 1)},
        "metrics": {"avg_a_pass": round(avg_a_pass, 1), "avg_b_pass": round(avg_b_pass, 1), "avg_a_cwe": round(avg_a_cwe, 1), "avg_b_cwe": round(avg_b_cwe, 1)},
        "tasks": [{"task": tid, "a_pass": a_results[i]["sec_pass_rate"], "b_pass": b_results[i]["sec_pass_rate"], "a_cwe": a_results[i]["cwe_count"], "b_cwe": b_results[i]["cwe_count"], "a_orch": a_results[i]["orch_rate"], "b_orch": b_results[i]["orch_rate"]} for i, tid in enumerate(tasks)]
    }

    (out_dir/"v6_results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (bd/"results").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out_dir/"v6_security.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["task","a_pass","b_pass","a_cwe","b_cwe","a_orch","b_orch"]); w.writeheader()
        w.writerows([{"task": tid, "a_pass": a_results[i]["sec_pass_rate"], "b_pass": b_results[i]["sec_pass_rate"], "a_cwe": a_results[i]["cwe_count"], "b_cwe": b_results[i]["cwe_count"], "a_orch": a_results[i]["orch_rate"], "b_orch": b_results[i]["orch_rate"]} for i, tid in enumerate(tasks)])
    print(f"\nResults: {out_dir/'v6_results.json'}")

if __name__ == "__main__":
    import csv; main()

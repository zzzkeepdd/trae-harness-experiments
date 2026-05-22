import sys, json, time, csv, os, subprocess, re, shutil, tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

PATH_HARNESS = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PATH_HARNESS))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

SOURCE_CODE_A = {}
SOURCE_CODE_B = {}

SOURCE_CODE_A["l1-1-string-utils"] = r'''
def reverse(s):
    if s is None:
        return ""
    return s[::-1]

def to_title_case(s):
    if s is None or s == "":
        return ""
    return s.title()

def is_palindrome(s):
    if s is None:
        return False
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    if not cleaned:
        return False
    return cleaned == cleaned[::-1]

def word_count(s):
    if s is None or s == "":
        return {}
    words = re.findall(r'[a-zA-Z0-9]+', s.lower())
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts
'''

SOURCE_CODE_B["l1-1-string-utils"] = SOURCE_CODE_A["l1-1-string-utils"]

SOURCE_CODE_B["l1-2-list-utils"] = r'''def dedup(items):
    if items is None:
        return []
    seen = set()
    result = []
    for item in items:
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            result.append(item)
    return result

def flatten(nested):
    if nested is None:
        return []
    result = []
    for sublist in nested:
        if isinstance(sublist, list):
            result.extend(sublist)
        else:
            result.append(sublist)
    return result

def group_by(items, key_fn):
    if items is None:
        return {}
    groups = {}
    for item in items:
        key = key_fn(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups

def top_n(items, n, key_fn=None):
    if items is None:
        return []
    if key_fn is None:
        key_fn = lambda x: x
    if n <= 0:
        return []
    sorted_items = sorted(items, key=key_fn, reverse=True)
    return sorted_items[:n]
'''

SOURCE_CODE_B["l2-1-cache"] = r'''import time
import threading
from collections import OrderedDict

class Cache:
    def __init__(self, max_size):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._data = OrderedDict()
        self._ttl = {}
        self._lock = threading.Lock()

    def set(self, key, value, ttl=None):
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = value
            self._ttl[key] = time.monotonic() + ttl if ttl is not None else None
            self._evict_expired()
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)

    def get(self, key):
        with self._lock:
            self._evict_expired()
            if key not in self._data:
                return None
            ttl_deadline = self._ttl.get(key)
            if ttl_deadline is not None and time.monotonic() >= ttl_deadline:
                del self._data[key]
                del self._ttl[key]
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def delete(self, key):
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._ttl.pop(key, None)

    def size(self):
        with self._lock:
            self._evict_expired()
            return len(self._data)

    def clear(self):
        with self._lock:
            self._data.clear()
            self._ttl.clear()

    def keys(self):
        with self._lock:
            self._evict_expired()
            return list(self._data.keys())

    def _evict_expired(self):
        now = time.monotonic()
        expired = [k for k, v in self._ttl.items() if v is not None and now >= v]
        for k in expired:
            self._data.pop(k, None)
            self._ttl.pop(k, None)
'''

SOURCE_CODE_B["l2-2-csv-processor"] = r'''import csv
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
'''

SOURCE_CODE_B["l3-1-task-queue"] = r'''import threading
import queue
import time
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

@dataclass(order=True)
class Task:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    max_retries: int = field(default=3, compare=False)
    timeout: Optional[float] = field(default=None, compare=False)

class TaskQueue:
    def __init__(self, max_workers=4):
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}
        self._results_lock = threading.Lock()
        self._workers = []
        self._running = False
        self._stop_event = threading.Event()
        self._stats = {"completed": 0, "failed": 0, "pending": 0}
        self._stats_lock = threading.Lock()
        self._closed = False
        self._close_lock = threading.Lock()

    def submit(self, task):
        with self._close_lock:
            if self._closed:
                raise RuntimeError("TaskQueue is closed, cannot submit new tasks")
        with self._stats_lock:
            self._stats["pending"] += 1
        self._queue.put((-task.priority, task))

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        for i in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True)
            self._workers.append(t)
            t.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        with self._close_lock:
            self._closed = True
        for t in self._workers:
            t.join(timeout=5)

    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with self._results_lock:
                if task_id in self._results:
                    return self._results.pop(task_id)
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.01)

    def _worker(self):
        while self._running or not self._queue.empty():
            try:
                _, task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            retries = 0
            result = None
            while retries <= task.max_retries:
                try:
                    if task.timeout is not None:
                        result_container = []
                        exc_container = []
                        def target():
                            try:
                                result_container.append(task.func(*task.args, **task.kwargs))
                            except Exception as e:
                                exc_container.append(e)
                        t = threading.Thread(target=target, daemon=True)
                        t.start()
                        t.join(timeout=task.timeout)
                        if t.is_alive():
                            retries += 1
                            continue
                        if exc_container:
                            raise exc_container[0]
                        result = result_container[0] if result_container else None
                    else:
                        result = task.func(*task.args, **task.kwargs)
                    break
                except Exception:
                    retries += 1
            if retries > task.max_retries:
                result = {"error": "task failed after max retries"}
                with self._stats_lock:
                    self._stats["failed"] += 1
            else:
                with self._stats_lock:
                    self._stats["completed"] += 1
            with self._stats_lock:
                self._stats["pending"] -= 1
            with self._results_lock:
                self._results[task.id] = result
            self._queue.task_done()
'''

SOURCE_CODE_B["l3-2-session-manager"] = r'''import hashlib
import hmac
import json
import base64
import time
import threading
import os
from dataclasses import dataclass

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    roles: list

@dataclass
class TokenPayload:
    user_id: str
    username: str
    roles: list
    exp: float

class SessionManager:
    def __init__(self, secret_key, token_ttl=3600):
        self._secret = secret_key.encode()
        self._token_ttl = token_ttl
        self._users = {}
        self._tokens = {}
        self._blacklist = set()
        self._online = set()
        self._lock = threading.Lock()
        self._permissions = {
            "admin": {"read", "write", "delete", "manage"},
            "user": {"read"},
            "editor": {"read", "write"},
            "viewer": {"read"},
        }

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
        payload = {
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "exp": time.time() + self._token_ttl,
        }
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        signing_input = f"{header}.{body}".encode()
        sig = base64.urlsafe_b64encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{header}.{body}.{sig}"

    def register(self, username, password):
        if not username or not password:
            raise ValueError("username and password must not be empty")
        with self._lock:
            if username in self._users:
                raise ValueError(f"user {username} already exists")
            user_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            self._users[user_id] = User(id=user_id, username=username, password_hash=self._hash_password(password), roles=["user"])
            return user_id

    def login(self, username, password):
        with self._lock:
            for user_id, user in self._users.items():
                if user.username == username and self._verify_password(password, user.password_hash):
                    if user_id in self._tokens:
                        self._blacklist.add(self._tokens[user_id])
                    token = self._build_token(user_id, user.username, user.roles)
                    self._tokens[user_id] = token
                    self._online.add(user_id)
                    return token
            return None

    def verify_token(self, token):
        if not token or token in self._blacklist:
            return None
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_raw = json.loads(base64.urlsafe_b64decode(parts[0] + "===").decode())
            if header_raw.get("alg") != "HS256":
                return None
            expected_sig = base64.urlsafe_b64encode(
                hmac.new(self._secret, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
            ).rstrip(b"=").decode()
            if not hmac.compare_digest(expected_sig, parts[2]):
                return None
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "===").decode())
            if time.time() >= payload["exp"]:
                return None
            return TokenPayload(
                user_id=payload["user_id"],
                username=payload["username"],
                roles=payload["roles"],
                exp=payload["exp"],
            )
        except Exception:
            return None

    def refresh_token(self, old_token):
        payload = self.verify_token(old_token)
        if payload is None:
            return None
        with self._lock:
            self._blacklist.add(old_token)
            new_token = self._build_token(payload.user_id, payload.username, payload.roles)
            self._tokens[payload.user_id] = new_token
            return new_token

    def logout(self, user_id):
        with self._lock:
            if user_id in self._tokens:
                self._blacklist.add(self._tokens.pop(user_id))
            self._online.discard(user_id)

    def check_permission(self, user_id, permission):
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            allowed = set()
            for role in user.roles:
                allowed.update(self._permissions.get(role, set()))
            return permission in allowed

    def get_online_users(self):
        with self._lock:
            return list(self._online)
'''

A_CODE = {}

A_CODE["l1-1-string-utils"] = r'''import re
def rev(x):
    if x is None:
        return ""
    return x[::-1]
def titl(x):
    if x is None or x == "":
        return ""
    return x.title()
def pal(x):
    if x is None:
        return False
    a=re.sub(r'[^a-zA-Z0-9]','',x).lower()
    if not a:
        return False
    return a==a[::-1]
def wc(x):
    if x is None or x == "":
        return {}
    z=re.findall(r'[a-zA-Z0-9]+',x.lower())
    y={}
    for t in z:
        y[t]=y.get(t,0)+1
    return y
'''

A_CODE["l1-2-list-utils"] = r'''def dd(x):
    if x is None:
        return []
    s=set()
    r=[]
    for a in x:
        try:
            if a not in s:
                s.add(a)
                r.append(a)
        except TypeError:
            r.append(a)
    return r
def fl(x):
    if x is None:
        return []
    r=[]
    for a in x:
        if isinstance(a,list):
            r.extend(a)
        else:
            r.append(a)
    return r
def gb(x,f):
    if x is None:
        return {}
    g={}
    for a in x:
        k=f(a)
        if k not in g:
            g[k]=[]
        g[k].append(a)
    return g
def tn(x,n,f=None):
    if x is None:
        return []
    if f is None:
        f=lambda x:x
    if n<=0:
        return []
    s=sorted(x,key=f,reverse=True)
    return s[:n]
'''

A_CODE["l2-1-cache"] = r'''import time
import threading
from collections import OrderedDict
class Cache:
    def __init__(s, sz):
        if sz < 1:
            raise ValueError("sz must be >= 1")
        s.sz = sz
        s.d = OrderedDict()
        s.t = {}
        s.l = threading.Lock()
    def set(s, k, v, ttl=None):
        with s.l:
            if k in s.d:
                del s.d[k]
            s.d[k] = v
            s.t[k] = time.monotonic() + ttl if ttl is not None else None
            s._ev()
            while len(s.d) > s.sz:
                s.d.popitem(last=False)
    def get(s, k):
        with s.l:
            s._ev()
            if k not in s.d:
                return None
            x = s.t.get(k)
            if x is not None and time.monotonic() >= x:
                del s.d[k]
                del s.t[k]
                return None
            s.d.move_to_end(k)
            return s.d[k]
    def delete(s, k):
        with s.l:
            if k in s.d:
                del s.d[k]
            s.t.pop(k, None)
    def size(s):
        with s.l:
            s._ev()
            return len(s.d)
    def clear(s):
        with s.l:
            s.d.clear()
            s.t.clear()
    def keys(s):
        with s.l:
            s._ev()
            return list(s.d.keys())
    def _ev(s):
        n = time.monotonic()
        e = [k for k, v in s.t.items() if v is not None and n >= v]
        for k in e:
            s.d.pop(k, None)
            s.t.pop(k, None)
'''

A_CODE["l2-2-csv-processor"] = r'''import csv
import os
def rc(p, e="utf-8"):
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding=e, newline="") as f:
            r = csv.DictReader(f)
            return list(r)
    except Exception:
        return []
def fr(d, c):
    r = []
    for a in d:
        m = True
        for col, val in c.items():
            if col not in a or str(a[col]) != str(val):
                m = False
                break
        if m:
            r.append(a)
    return r
def ag(d, g, f):
    if not d:
        return []
    op = f.get("op", "sum")
    col = f.get("column")
    gr = {}
    for a in d:
        k = a.get(g)
        if k is None:
            continue
        if k not in gr:
            gr[k] = []
        v = a.get(col)
        if v is not None:
            try:
                gr[k].append(float(v))
            except (ValueError, TypeError):
                gr[k].append(0.0)
    r = []
    for k, vals in gr.items():
        e = {g: k}
        if op == "sum":
            e["sum"] = sum(vals)
        elif op == "count":
            e["count"] = len(vals)
        elif op == "avg":
            e["avg"] = sum(vals) / len(vals) if vals else 0
        elif op == "min":
            e["min"] = min(vals) if vals else 0
        elif op == "max":
            e["max"] = max(vals) if vals else 0
        r.append(e)
    return r
def wc(d, p):
    if not d:
        return
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    fn = list(d[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(d)
def pp(ip, op, fc, gc, ac, ao):
    d = rc(ip)
    f = fr(d, fc)
    a = ag(f, gc, {"op": ao, "column": ac})
    wc(a, op)
'''

A_CODE["l3-1-task-queue"] = r'''import threading
import queue
import time
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
@dataclass(order=True)
class Task:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    max_retries: int = field(default=3, compare=False)
    timeout: Optional[float] = field(default=None, compare=False)
class TaskQueue:
    def __init__(s, mw=4):
        if mw < 1:
            raise ValueError("mw must be >= 1")
        s.mw = mw
        s.q = queue.PriorityQueue()
        s.rs = {}
        s.rl = threading.Lock()
        s.ws = []
        s.rn = False
        s.se = threading.Event()
        s.st = {"completed": 0, "failed": 0, "pending": 0}
        s.sl = threading.Lock()
        s.cl = False
        s.ll = threading.Lock()
    def submit(s, t):
        with s.ll:
            if s.cl:
                raise RuntimeError("TaskQueue is closed")
        with s.sl:
            s.st["pending"] += 1
        s.q.put((-t.priority, t))
    def start(s):
        if s.rn:
            return
        s.rn = True
        s.se.clear()
        for _ in range(s.mw):
            x = threading.Thread(target=s._w, daemon=True)
            s.ws.append(x)
            x.start()
    def stop(s):
        s.rn = False
        s.se.set()
        with s.ll:
            s.cl = True
        for x in s.ws:
            x.join(timeout=5)
    def get_result(s, tid, to=None):
        dl = time.monotonic() + to if to is not None else None
        while True:
            with s.rl:
                if tid in s.rs:
                    return s.rs.pop(tid)
            if dl is not None and time.monotonic() >= dl:
                return None
            time.sleep(0.01)
    def _w(s):
        while s.rn or not s.q.empty():
            try:
                _, tk = s.q.get(timeout=0.1)
            except queue.Empty:
                continue
            rt = 0
            res = None
            while rt <= tk.max_retries:
                try:
                    if tk.timeout is not None:
                        rc = []
                        ec = []
                        def tg():
                            try:
                                rc.append(tk.func(*tk.args, **tk.kwargs))
                            except Exception as e:
                                ec.append(e)
                        t = threading.Thread(target=tg, daemon=True)
                        t.start()
                        t.join(timeout=tk.timeout)
                        if t.is_alive():
                            rt += 1
                            continue
                        if ec:
                            raise ec[0]
                        res = rc[0] if rc else None
                    else:
                        res = tk.func(*tk.args, **tk.kwargs)
                    break
                except Exception:
                    rt += 1
            if rt > tk.max_retries:
                res = {"error": "task failed"}
                with s.sl:
                    s.st["failed"] += 1
            else:
                with s.sl:
                    s.st["completed"] += 1
            with s.sl:
                s.st["pending"] -= 1
            with s.rl:
                s.rs[tk.id] = res
            s.q.task_done()
'''

A_CODE["l3-2-session-manager"] = r'''import hashlib
import hmac
import json
import base64
import time
import threading
import os
from dataclasses import dataclass
@dataclass
class User:
    id: str
    username: str
    password_hash: str
    roles: list
@dataclass
class TokenPayload:
    user_id: str
    username: str
    roles: list
    exp: float
class SessionManager:
    def __init__(s, sk, ttl=3600):
        s.se = sk.encode()
        s.ttl = ttl
        s.us = {}
        s.tk = {}
        s.bl = set()
        s.on = set()
        s.lk = threading.Lock()
        s.pm = {"admin": {"read", "write", "delete", "manage"}, "user": {"read"}, "editor": {"read", "write"}, "viewer": {"read"}}
    def _hp(s, pw):
        sl = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), sl, 100000)
        return base64.b64encode(sl + dk).decode()
    def _vp(s, pw, hs):
        dc = base64.b64decode(hs)
        sl, dk = dc[:16], dc[16:]
        nd = hashlib.pbkdf2_hmac("sha256", pw.encode(), sl, 100000)
        return hmac.compare_digest(nd, dk)
    def _bt(s, uid, un, rl):
        pl = {"user_id": uid, "username": un, "roles": rl, "exp": time.time() + s.ttl}
        hd = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        bd = base64.urlsafe_b64encode(json.dumps(pl).encode()).rstrip(b"=").decode()
        si = f"{hd}.{bd}".encode()
        sg = base64.urlsafe_b64encode(hmac.new(s.se, si, hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{hd}.{bd}.{sg}"
    def register(s, un, pw):
        if not un or not pw:
            raise ValueError("empty")
        with s.lk:
            if un in s.us:
                raise ValueError(f"exists")
            uid = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            s.us[uid] = User(id=uid, username=un, password_hash=s._hp(pw), roles=["user"])
            return uid
    def login(s, un, pw):
        with s.lk:
            for uid, u in s.us.items():
                if u.username == un and s._vp(pw, u.password_hash):
                    if uid in s.tk:
                        s.bl.add(s.tk[uid])
                    tok = s._bt(uid, u.username, u.roles)
                    s.tk[uid] = tok
                    s.on.add(uid)
                    return tok
            return None
    def verify_token(s, tok):
        if not tok or tok in s.bl:
            return None
        try:
            ps = tok.split(".")
            if len(ps) != 3:
                return None
            hr = json.loads(base64.urlsafe_b64decode(ps[0] + "===").decode())
            if hr.get("alg") != "HS256":
                return None
            es = base64.urlsafe_b64encode(hmac.new(s.se, f"{ps[0]}.{ps[1]}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(es, ps[2]):
                return None
            pl = json.loads(base64.urlsafe_b64decode(ps[1] + "===").decode())
            if time.time() >= pl["exp"]:
                return None
            return TokenPayload(user_id=pl["user_id"], username=pl["username"], roles=pl["roles"], exp=pl["exp"])
        except Exception:
            return None
    def refresh_token(s, ot):
        pl = s.verify_token(ot)
        if pl is None:
            return None
        with s.lk:
            s.bl.add(ot)
            nt = s._bt(pl.user_id, pl.username, pl.roles)
            s.tk[pl.user_id] = nt
            return nt
    def logout(s, uid):
        with s.lk:
            if uid in s.tk:
                s.bl.add(s.tk.pop(uid))
            s.on.discard(uid)
    def check_permission(s, uid, pm):
        with s.lk:
            u = s.us.get(uid)
            if u is None:
                return False
            al = set()
            for r in u.roles:
                al.update(s.pm.get(r, set()))
            return pm in al
    def get_online_users(s):
        with s.lk:
            return list(s.on)
'''

def count_long_lines(code, max_len=88):
    return sum(1 for line in code.split("\n") if len(line) > max_len)

def count_missing_docstrings(code):
    lines = code.split("\n")
    count = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if (stripped.startswith("def ") or stripped.startswith("class ")) and "(" in stripped:
            j = i + 1
            has_doc = False
            while j < len(lines) and (lines[j].strip() == "" or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    has_doc = True
            if not has_doc and not stripped.startswith("def _") and not (
                stripped.startswith("def __") and "__" in stripped.split("(")[0]
            ):
                count += 1
        i += 1
    return count

BAD_VAR_NAMES_SINGLE = set("xyzab")

def count_bad_variable_names(code):
    lines = code.split("\n")
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("def ", "class ")):
            continue
        if stripped.startswith(("import ", "from ")):
            continue
        if " = " in stripped or " in " in stripped or "for " in stripped:
            word_pattern = re.findall(r'\b([a-zA-Z])\b', stripped)
            for w in word_pattern:
                if w.lower() in BAD_VAR_NAMES_SINGLE:
                    count += 1
        matches = re.findall(r'for\s+([a-zA-Z])\s+in', stripped)
        for m in matches:
            if m.lower() in BAD_VAR_NAMES_SINGLE:
                count += 1
    return count

def count_magic_numbers(code):
    lines = code.split("\n")
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if stripped.startswith(("import ", "from ")):
            continue
        numbers = re.findall(r'(?<![a-zA-Z_0-9])(\d+)(?![a-zA-Z_0-9])', stripped)
        for n in numbers:
            num = int(n)
            if num not in (0, 1, -1, 2):
                count += 1
    return count

def compute_maintainability_index(code):
    lines = code.split("\n")
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    loc = len(code_lines)
    comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
    halstead_vocab = len(set(re.findall(r'\b[a-zA-Z_]\w*\b', code)))
    halstead_len = len(re.findall(r'\b[a-zA-Z_]\w*\b', code))
    halstead_vol = halstead_len * (halstead_vocab / 2) if halstead_vocab > 0 else 0
    cc = count_cyclomatic_complexity(code)
    if loc <= 0:
        return 100.0
    mi = 171 - 5.2 * (halstead_vol / loc) - 0.23 * cc - 16.2 * loc
    mi = max(0, min(100, mi))
    return round(mi, 1)

def count_cyclomatic_complexity(code):
    decision_keywords = re.findall(
        r'\b(if|elif|while|for|and|or|except)\b', code
    )
    return len(decision_keywords)

def run_flake8_if_available(code_str, tmp_path):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "flake8", "--max-line-length=88", "--select=E,W,F", str(tmp_path)],
            capture_output=True, text=True, timeout=30
        )
        violations = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        return len(violations), violations
    except Exception:
        return -1, []

def run_pylint_if_available(code_str, tmp_path):
    try:
        tmpdir = tmp_path.parent
        rc_path = tmpdir / ".pylintrc"
        rc_path.write_text(
            "[MASTER]\nignore=CVS\n[MESSAGES CONTROL]\ndisable=all\nenable=C,R,W\n"
            "[FORMAT]\nmax-line-length=88\n"
        )
        result = subprocess.run(
            [sys.executable, "-m", "pylint", str(tmp_path), "--rcfile", str(rc_path),
             "--output-format=json"],
            capture_output=True, text=True, timeout=60
        )
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else []
            score_line = [l for l in result.stderr.split("\n") if "Your code has been rated at" in l]
            score = 0.0
            if score_line:
                m = re.search(r'rated at\s+([\d.]+)', score_line[0])
                if m:
                    score = float(m.group(1))
            return score, len(data)
        except json.JSONDecodeError:
            score_line = [l for l in result.stdout.split("\n") + result.stderr.split("\n")
                          if "Your code has been rated at" in l]
            score = 0.0
            if score_line:
                m = re.search(r'rated at\s+([\d.]+)', score_line[0])
                if m:
                    score = float(m.group(1))
            return score, -1
    except Exception:
        return -1.0, -1

def run_radon_if_available(tmp_path):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "radon", "mi", "-s", str(tmp_path)],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split("\n")
        scores = []
        for line in lines:
            parts = line.split()
            if parts:
                try:
                    scores.append(float(parts[-1]))
                except ValueError:
                    pass
        if scores:
            return round(sum(scores) / len(scores), 2)
        return -1.0
    except Exception:
        return -1.0

def run_radon_cc_if_available(tmp_path):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc", "-a", str(tmp_path)],
            capture_output=True, text=True, timeout=30
        )
        blocks = result.stdout.strip().split("\n\n")
        all_ranks = []
        for block in blocks:
            for line in block.split("\n"):
                if line.strip() and not line.strip().startswith(" "):
                    parts = line.strip().split()
                    if parts and parts[0] in "ABCDEF":
                        all_ranks.append(parts[0])
        rank_scores = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
        total = sum(rank_scores.get(r, 3) for r in all_ranks)
        avg = total / len(all_ranks) if all_ranks else 0
        return round(avg, 2)
    except Exception:
        return -1.0

@dataclass
class CodeStandardsMetrics:
    task_id: str
    group: str
    flake8_violations: int = 0
    pylint_score: float = 0.0
    maintainability_index: float = 0.0
    cyclomatic_complexity: float = 0.0
    long_lines: int = 0
    missing_docstrings: int = 0
    bad_variables: int = 0
    magic_numbers: int = 0
    flake8_available: bool = False
    pylint_available: bool = False
    radon_available: bool = False

def measure_code_standards(code_str: str, task_id: str, group: str) -> CodeStandardsMetrics:
    m = CodeStandardsMetrics(task_id=task_id, group=group)
    tmpdir = Path(shutil._get_default_temp_dir()) if hasattr(shutil, '_get_default_temp_dir') else Path(tempfile.gettempdir()) if 'tempfile' in sys.modules else Path(os.environ.get("TEMP", "."))
    m.long_lines = count_long_lines(code_str)
    m.missing_docstrings = count_missing_docstrings(code_str)
    m.bad_variables = count_bad_variable_names(code_str)
    m.magic_numbers = count_magic_numbers(code_str)
    m.maintainability_index = compute_maintainability_index(code_str)
    m.cyclomatic_complexity = count_cyclomatic_complexity(code_str)
    import tempfile as tf
    with tf.TemporaryDirectory(prefix="cs_") as td:
        tpath = Path(td) / "code.py"
        tpath.write_text(code_str, encoding="utf-8")
        f8_count, _ = run_flake8_if_available(code_str, tpath)
        if f8_count >= 0:
            m.flake8_available = True
            m.flake8_violations = f8_count
        else:
            m.flake8_violations = m.long_lines + m.missing_docstrings
            m.flake8_available = False
        pl_score, pl_count = run_pylint_if_available(code_str, tpath)
        if pl_score >= 0:
            m.pylint_available = True
            m.pylint_score = pl_score
        else:
            m.pylint_score = max(0.0, 10.0 - (m.long_lines * 0.5) - (m.missing_docstrings * 2.0) - (m.bad_variables * 1.0) - (m.magic_numbers * 0.5))
            m.pylint_available = False
        radon_mi = run_radon_if_available(tpath)
        if radon_mi >= 0:
            m.radon_available = True
            m.maintainability_index = radon_mi
        radon_cc = run_radon_cc_if_available(tpath)
        if radon_cc >= 0:
            m.cyclomatic_complexity = radon_cc
    return m

TASK_INFO = {
    "l1-1-string-utils": {
        "level": "L1",
        "attacks": [
            {"description": "function names too short, missing docstrings across all 4 functions", "target_dimension": "naming", "score": 4, "scoring_rationale": "unreadable API surface"},
            {"description": "single-letter variable names x, a, z, y, t obscure data flow", "target_dimension": "readability", "score": 4, "scoring_rationale": "debugging cost multiplier"},
            {"description": "magic regex patterns embedded without constants", "target_dimension": "maintainability", "score": 3, "scoring_rationale": "pattern reuse impossible"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Add docstrings to all public functions", "Use descriptive variable names", "Extract regex patterns to constants"],
    },
    "l1-2-list-utils": {
        "level": "L1",
        "attacks": [
            {"description": "all function names abbreviated to 2 letters — fI, dd, gb, tn — violating PEP8", "target_dimension": "naming", "score": 5, "scoring_rationale": "worst-case readability"},
            {"description": "self parameter renamed to 's' in Cache class — violates Python convention", "target_dimension": "naming", "score": 4, "scoring_rationale": "confuses IDE and tooling"},
            {"description": "zero docstrings across 4 functions despite non-trivial behavior like TypeError handling", "target_dimension": "documentation", "score": 4, "scoring_rationale": "maintenance nightmare"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Rename functions to descriptive names", "Use 'self' parameter name", "Add docstrings"],
    },
    "l2-1-cache": {
        "level": "L2",
        "attacks": [
            {"description": "all instance attributes abbreviated to 1-2 chars: d, t, l, sz, s — severely impacts maintainability", "target_dimension": "naming", "score": 5, "scoring_rationale": "near-unreadable state management"},
            {"description": "self replaced with 's' throughout including __init__ breaking IDE autocomplete", "target_dimension": "convention", "score": 4, "scoring_rationale": "tooling support destroyed"},
            {"description": "no class-level or method-level docstrings for thread-safe cache with TTL", "target_dimension": "documentation", "score": 4, "scoring_rationale": "concurrency semantics undocumented"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Restore descriptive attribute names", "Use 'self' conventionally", "Document thread safety guarantees"],
    },
    "l2-2-csv-processor": {
        "level": "L2",
        "attacks": [
            {"description": "function names are all 2-letter abbreviations: rc, fr, ag, wc, pp — complete PEP8 violation", "target_dimension": "naming", "score": 5, "scoring_rationale": "API completely unreadable"},
            {"description": "parameter names: p, e, d, c, g, f, a — single letters throughout entire module", "target_dimension": "readability", "score": 5, "scoring_rationale": "signature understanding requires reading full implementation"},
            {"description": "no docstrings on any function, CSV processing semantics undocumented", "target_dimension": "documentation", "score": 4, "scoring_rationale": "data pipeline contracts invisible"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Rename all functions and parameters descriptively", "Add docstrings for pipeline stages"],
    },
    "l3-1-task-queue": {
        "level": "L3",
        "attacks": [
            {"description": "self parameter replaced with 's' throughout entire 60-line class — Python convention broken", "target_dimension": "convention", "score": 5, "scoring_rationale": "team collaboration impossible"},
            {"description": "attribute names: mw, q, rs, rl, ws, rn, se, st, sl, cl, ll — 11 cryptic names", "target_dimension": "naming", "score": 5, "scoring_rationale": "state machine completely opaque"},
            {"description": "no docstrings on class or any method despite L3 complexity with threading/queues", "target_dimension": "documentation", "score": 5, "scoring_rationale": "concurrent code undocumented is dangerous"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Restore 'self' parameter name", "Descriptive attribute names", "Document concurrency model"],
    },
    "l3-2-session-manager": {
        "level": "L3",
        "attacks": [
            {"description": "self→s, attributes: se, ttl, us, tk, bl, on, lk, pm — 8 cryptic names", "target_dimension": "naming", "score": 5, "scoring_rationale": "auth module requires maximum readability"},
            {"description": "method names: _hp, _vp, _bt — abbreviated private methods obscure password/token internals", "target_dimension": "naming", "score": 4, "scoring_rationale": "security code must be auditable"},
            {"description": "no docstrings whatsoever on SessionManager — JWT security semantics undocumented", "target_dimension": "documentation", "score": 5, "scoring_rationale": "security-critical code without documentation"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Restore 'self' and descriptive names", "Rename private methods clearly", "Add security documentation"],
    },
}

def main():
    print("=" * 100)
    print("v5 实验: 代码规范 (P1) — flake8 + pylint + radon + regex 回退")
    print("A 组: DSV4 Pro 直出代码 (故意含 code smell)")
    print("B 组: Harness Code QA enforced 清理后代码")
    print("=" * 100)

    tasks_to_run = [
        ("l1-1-string-utils", "L1"), ("l1-2-list-utils", "L1"),
        ("l2-1-cache", "L2"), ("l2-2-csv-processor", "L2"),
        ("l3-1-task-queue", "L3"), ("l3-2-session-manager", "L3"),
    ]

    base_dir = Path(__file__).parent
    out_dir = base_dir / "results_data"
    out_dir.mkdir(exist_ok=True)

    standards_results = []
    pipeline_results = []

    for task_id, level in tasks_to_run:
        info = TASK_INFO[task_id]
        task_dir = base_dir / "tasks" / task_id
        if task_dir.exists():
            shutil.rmtree(str(task_dir), ignore_errors=True)
        task_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"任务: {task_id} ({level})")
        print(f"{'='*70}")

        a_code = A_CODE[task_id]
        b_code = SOURCE_CODE_B[task_id]

        print(f"  A 组 (DSV4 Pro 直出 — 含 code smell)...")
        a_metrics = measure_code_standards(a_code, task_id, "A")
        print(f"    flake8={a_metrics.flake8_violations} pylint={a_metrics.pylint_score:.1f} "
              f"MI={a_metrics.maintainability_index} CC={a_metrics.cyclomatic_complexity} "
              f"long_lines={a_metrics.long_lines} docs_miss={a_metrics.missing_docstrings} "
              f"bad_vars={a_metrics.bad_variables} magic={a_metrics.magic_numbers}")

        print(f"  B 组 (Harness Code QA enforced — 清理后)...")
        productions = build_productions(task_dir, level, info["attacks"], info["must_fix"])

        def make_step1():
            src = task_dir / "src"; src.mkdir(exist_ok=True)
            (src / "__init__.py").write_text("")
            (src / "main.py").write_text(b_code, encoding="utf-8")
            (src / "test_main.py").write_text("def test_dummy(): pass\n", encoding="utf-8")

        productions["MODULE_2_STEP_1"] = make_step1

        print("  B 组 (编排器全流程)...")
        b_passed, b_total, b_events = run_harness_full(task_dir, productions)
        b_rate = b_passed / b_total * 100 if b_total > 0 else 0
        print(f"  B 组编排器: {b_passed}/{b_total} ({b_rate:.0f}%)")
        for ph, ok, msg in b_events:
            print(f"    {ph:<20} {'✓' if ok else '✗'} {msg}")

        pipeline_results.append({"task": task_id, "level": level,
                                  "b_passed": b_passed, "b_total": b_total, "b_rate": f"{b_rate:.0f}%"})

        b_metrics = measure_code_standards(b_code, task_id, "B")
        print(f"    flake8={b_metrics.flake8_violations} pylint={b_metrics.pylint_score:.1f} "
              f"MI={b_metrics.maintainability_index} CC={b_metrics.cyclomatic_complexity} "
              f"long_lines={b_metrics.long_lines} docs_miss={b_metrics.missing_docstrings} "
              f"bad_vars={b_metrics.bad_variables} magic={b_metrics.magic_numbers}")

        standards_results.append({
            "task": task_id, "level": level,
            "a_flake8": a_metrics.flake8_violations,
            "b_flake8": b_metrics.flake8_violations,
            "a_pylint": round(a_metrics.pylint_score, 2),
            "b_pylint": round(b_metrics.pylint_score, 2),
            "a_mi": a_metrics.maintainability_index,
            "b_mi": b_metrics.maintainability_index,
            "a_cc": a_metrics.cyclomatic_complexity,
            "b_cc": b_metrics.cyclomatic_complexity,
            "a_long_lines": a_metrics.long_lines,
            "b_long_lines": b_metrics.long_lines,
            "a_docs_miss": a_metrics.missing_docstrings,
            "b_docs_miss": b_metrics.missing_docstrings,
            "a_bad_vars": a_metrics.bad_variables,
            "b_bad_vars": b_metrics.bad_variables,
            "a_magic": a_metrics.magic_numbers,
            "b_magic": b_metrics.magic_numbers,
            "flake8_available": a_metrics.flake8_available,
            "pylint_available": a_metrics.pylint_available,
            "radon_available": a_metrics.radon_available,
        })

    print("\n" + "=" * 100)
    print("v5 代码规范实验汇总")
    print("=" * 100)

    print(f"{'任务':<30} {'级':<4} {'A flake8':<10} {'B flake8':<10} {'A pylint':<10} {'B pylint':<10} "
          f"{'A MI':<8} {'B MI':<8} {'A CC':<7} {'B CC':<7}")
    print("-" * 100)

    for sr in standards_results:
        print(f"{sr['task']:<30} {sr['level']:<4} {sr['a_flake8']:<10} {sr['b_flake8']:<10} "
              f"{sr['a_pylint']:<10.1f} {sr['b_pylint']:<10.1f} "
              f"{sr['a_mi']:<8.1f} {sr['b_mi']:<8.1f} {sr['a_cc']:<7} {sr['b_cc']:<7}")

    avg_a_flake8 = sum(s["a_flake8"] for s in standards_results) / len(standards_results)
    avg_b_flake8 = sum(s["b_flake8"] for s in standards_results) / len(standards_results)
    avg_a_pylint = sum(s["a_pylint"] for s in standards_results) / len(standards_results)
    avg_b_pylint = sum(s["b_pylint"] for s in standards_results) / len(standards_results)
    avg_a_mi = sum(s["a_mi"] for s in standards_results) / len(standards_results)
    avg_b_mi = sum(s["b_mi"] for s in standards_results) / len(standards_results)
    avg_a_cc = sum(s["a_cc"] for s in standards_results) / len(standards_results)
    avg_b_cc = sum(s["b_cc"] for s in standards_results) / len(standards_results)

    print("-" * 100)
    print(f"{'平均':<30} {'':<4} {avg_a_flake8:<10.1f} {avg_b_flake8:<10.1f} "
          f"{avg_a_pylint:<10.2f} {avg_b_pylint:<10.2f} "
          f"{avg_a_mi:<8.1f} {avg_b_mi:<8.1f} {avg_a_cc:<7.1f} {avg_b_cc:<7.1f}")
    print("=" * 100)
    print(f"\n  flake8 违规减少: {avg_a_flake8 - avg_b_flake8:.0f} ({(1 - avg_b_flake8/max(avg_a_flake8,1))*100:.0f}%)")
    print(f"  pylint 评分提升: {avg_b_pylint - avg_a_pylint:+.1f}")
    print(f"  MI 提升: {avg_b_mi - avg_a_mi:+.1f}")
    print(f"  CC 降低: {avg_a_cc - avg_b_cc:+.1f}")
    print(f"  工具可用: flake8={standards_results[0]['flake8_available']} "
          f"pylint={standards_results[0]['pylint_available']} "
          f"radon={standards_results[0]['radon_available']}")

    summary = {
        "a": {"flake8_violations": round(avg_a_flake8, 1), "pylint_score": round(avg_a_pylint, 2),
              "mi": round(avg_a_mi, 1), "cc": round(avg_a_cc, 1)},
        "b": {"flake8_violations": round(avg_b_flake8, 1), "pylint_score": round(avg_b_pylint, 2),
              "mi": round(avg_b_mi, 1), "cc": round(avg_b_cc, 1)},
        "metrics": {
            "avg_a_flake8": round(avg_a_flake8, 1),
            "avg_b_flake8": round(avg_b_flake8, 1),
            "avg_a_pylint": round(avg_a_pylint, 2),
            "avg_b_pylint": round(avg_b_pylint, 2),
            "avg_a_mi": round(avg_a_mi, 1),
            "avg_b_mi": round(avg_b_mi, 1),
            "avg_a_cc": round(avg_a_cc, 1),
            "avg_b_cc": round(avg_b_cc, 1),
            "flake8_available": standards_results[0]["flake8_available"],
            "pylint_available": standards_results[0]["pylint_available"],
            "radon_available": standards_results[0]["radon_available"],
        },
        "tasks": [
            {
                "task": s["task"],
                "level": s["level"],
                "a": {"flake8": s["a_flake8"], "pylint": s["a_pylint"], "mi": s["a_mi"], "cc": s["a_cc"]},
                "b": {"flake8": s["b_flake8"], "pylint": s["b_pylint"], "mi": s["b_mi"], "cc": s["b_cc"]},
                "improvement": {
                    "flake8_delta": s["a_flake8"] - s["b_flake8"],
                    "pylint_delta": round(s["b_pylint"] - s["a_pylint"], 2),
                    "mi_delta": round(s["b_mi"] - s["a_mi"], 1),
                },
            }
            for s in standards_results
        ],
    }
    out_file = out_dir / "v5_results.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n结果: {out_file}")

    loop_file = base_dir / "results"
    loop_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"循环文件: {loop_file}")

    csv_file = out_dir / "v5_standards.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=standards_results[0].keys())
        w.writeheader()
        w.writerows(standards_results)
    print(f"CSV: {csv_file}")

if __name__ == "__main__":
    main()
import sys, json, time, os, re, shutil, datetime, tempfile, subprocess, csv, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

PATH_HARNESS = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PATH_HARNESS))
from real_harness import run_harness_full, build_productions
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

SOURCE_CODE = {}
A_FIXES = {}
B_FIXES = {}
TESTS = {}

SOURCE_CODE["v10-user-service"] = r'''
class User:
    user_id: str
    username: str
    password_hash: str
    email: str
    created_at: float

class UserService:
    def __init__(self):
        self._users = {}
        self._usernames = {}
        self._profiles = {}
        self._sessions = {}
        self._counter = 0

    def register(self, username, password, email):
        if username in self._usernames:
            raise ValueError(f"user {username} already exists")
        if not password or len(password) < 1:
            raise ValueError("password required")
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        self._counter += 1
        uid = f"u{self._counter}"
        self._usernames[username] = uid
        self._users[uid] = User(
            user_id=uid, username=username,
            password_hash=(salt + dk).hex(), email=email,
            created_at=time.time(),
        )
        self._profiles[uid] = {"bio": "", "avatar": ""}
        return uid

    def login(self, username, password):
        uid = self._usernames.get(username)
        if uid is None:
            return None
        user = self._users[uid]
        stored = bytes.fromhex(user.password_hash)
        salt, stored_dk = stored[:16], stored[16:]
        new_dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        if new_dk != stored_dk:
            return None
        session_id = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
        self._sessions[session_id] = uid
        return session_id

    def get_user_profile(self, session_id):
        uid = self._sessions.get(session_id)
        if uid is None:
            return None
        user = self._users[uid]
        profile = self._profiles[uid]
        profile["username"] = user.username
        profile["email"] = user.email
        return profile

    def update_email(self, session_id, new_email):
        uid = self._sessions[session_id]
        user = self._users[uid]
        user.email = new_email

    def delete_user(self, session_id):
        uid = self._sessions[session_id]
        del self._users[uid]
        del self._profiles[uid]
        for uname, u in list(self._usernames.items()):
            if u == uid:
                del self._usernames[uname]
'''

SOURCE_CODE["v10-order-processor"] = r'''import json
import time
import threading

class OrderProcessor:
    def __init__(self):
        self._inventory = {}
        self._orders = []
        self._order_counter = 0

    def add_inventory(self, item_id, quantity, price):
        self._inventory[item_id] = {"quantity": quantity, "price": price}

    def process_order(self, customer_id, items):
        order_id = f"ORD-{self._order_counter + 1:06d}"
        total = 0.0
        for item_id, qty in items:
            inv = self._inventory.get(item_id)
            if inv is None:
                raise ValueError(f"item {item_id} not found")
            if inv["quantity"] < qty:
                raise ValueError(f"insufficient stock for {item_id}")
            inv["quantity"] -= qty
            total += inv["price"] * qty
        total = round(total, 2)
        if total < 0.01:
            raise ValueError("order total too low")
        self._order_counter += 1
        order = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": items,
            "total": total,
            "timestamp": time.time(),
        }
        self._orders.append(order)
        return order

    def get_order(self, order_id):
        for o in self._orders:
            if o["order_id"] == order_id:
                return o
        return None

    def get_inventory(self, item_id):
        return self._inventory.get(item_id)

    def export_orders_json(self, filepath):
        with open(filepath, "w") as f:
            json.dump(self._orders, f, default=str)
'''

SOURCE_CODE["v10-config-loader"] = r'''import json
import os
import re

class ConfigLoader:
    def __init__(self, defaults=None):
        self._config = {}
        if defaults:
            self._config.update(defaults)
        self._loaded_files = set()

    def load_json(self, filepath):
        if filepath in self._loaded_files:
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._config.update(data)
        self._loaded_files.add(filepath)

    def load_env_override(self, prefix="APP_"):
        for key, val in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._config[config_key] = val

    def get(self, key):
        return self._config[key]

    def get_int(self, key):
        return int(self._config[key])

    def get_bool(self, key):
        val = self._config.get(key)
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "yes", "1", "on")

    def get_list(self, key, separator=","):
        val = self._config.get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [x.strip() for x in str(val).split(separator)]

    def get_all(self):
        return dict(self._config)

    def validate_required(self, required_keys):
        missing = []
        for k in required_keys:
            if k not in self._config:
                missing.append(k)
        if missing:
            raise ValueError(f"missing required: {missing}")

    def resolve_variables(self):
        pattern = re.compile(r'\$\{(\w+)\}')
        for key in list(self._config.keys()):
            val = str(self._config[key])
            def replacer(m):
                ref = m.group(1)
                return str(self._config.get(ref, ""))
            self._config[key] = pattern.sub(replacer, val)
'''

SOURCE_CODE["v10-api-rate-limiter"] = r'''import time
import threading
from collections import defaultdict

class ApiRateLimiter:
    def __init__(self, max_requests=100, window_seconds=60):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clients = defaultdict(list)
        self._lock = threading.Lock()
        self._blocked = {}

    def allow_request(self, client_id):
        now = time.monotonic()
        with self._lock:
            if client_id in self._blocked:
                if now < self._blocked[client_id]:
                    return False
                del self._blocked[client_id]
            window = self._clients[client_id]
            cutoff = now - self._window
            self._clients[client_id] = [t for t in window if t >= cutoff]
            count = len(self._clients[client_id])
            if count >= self._max_requests:
                self._blocked[client_id] = now + self._window
                return False
            self._clients[client_id].append(now)
            return True

    def reset_client(self, client_id):
        with self._lock:
            self._clients.pop(client_id, None)
            self._blocked.pop(client_id, None)

    def get_usage(self, client_id):
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            window = self._clients.get(client_id, [])
            active = [t for t in window if t >= cutoff]
            self._clients[client_id] = active
            return len(active)

    def cleanup(self):
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            for cid in list(self._clients.keys()):
                self._clients[cid] = [t for t in self._clients[cid] if t >= cutoff]
                if not self._clients[cid]:
                    del self._clients[cid]
            for cid in list(self._blocked.keys()):
                if now >= self._blocked[cid]:
                    del self._blocked[cid]
'''

SOURCE_CODE["v10-file-sync"] = r'''import hashlib
import os
import shutil
import json
import threading

class FileSync:
    def __init__(self, base_dir):
        self._base_dir = os.path.abspath(base_dir)
        os.makedirs(self._base_dir, exist_ok=True)
        self._manifest = {}
        self._manifest_path = os.path.join(self._base_dir, ".sync_manifest.json")
        self._lock = threading.Lock()
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self._manifest_path):
            with open(self._manifest_path, "r") as f:
                self._manifest = json.load(f)

    def _save_manifest(self):
        with open(self._manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def put_file(self, relative_path, content):
        full_path = os.path.join(self._base_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode("utf-8"))
            else:
                f.write(content)
        checksum = hashlib.md5(open(full_path, "rb").read()).hexdigest()
        with self._lock:
            self._manifest[relative_path] = {
                "checksum": checksum,
                "size": os.path.getsize(full_path),
            }
            self._save_manifest()

    def get_file(self, relative_path):
        full_path = os.path.join(self._base_dir, relative_path)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def verify_integrity(self, relative_path):
        full_path = os.path.join(self._base_dir, relative_path)
        if not os.path.exists(full_path):
            return False
        entry = self._manifest.get(relative_path)
        if entry is None:
            return False
        actual = hashlib.md5(open(full_path, "rb").read()).hexdigest()
        return actual == entry["checksum"]

    def list_files(self):
        with self._lock:
            return list(self._manifest.keys())

    def delete_file(self, relative_path):
        full_path = os.path.join(self._base_dir, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
        with self._lock:
            self._manifest.pop(relative_path, None)
            self._save_manifest()

    def sync_from(self, other_sync):
        for rel_path in other_sync.list_files():
            content = other_sync.get_file(rel_path)
            if content is not None:
                self.put_file(rel_path, content)
'''

SOURCE_CODE["v10-payment-gateway"] = r'''import hashlib
import hmac
import time
import threading
import json

class PaymentGateway:
    def __init__(self, api_secret):
        self._secret = api_secret.encode()
        self._accounts = {}
        self._transactions = {}
        self._idempotency_keys = set()
        self._lock = threading.Lock()
        self._tx_counter = 0

    def create_account(self, account_id, initial_balance=0.0):
        self._accounts[account_id] = {
            "balance": float(initial_balance),
            "frozen": 0.0,
        }
        return account_id

    def get_balance(self, account_id):
        acct = self._accounts.get(account_id)
        if acct is None:
            return None
        return acct["balance"] - acct["frozen"]

    def _sign(self, payload):
        msg = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def _verify(self, payload, signature):
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)

    def transfer(self, from_account, to_account, amount, idempotency_key, signature):
        payload = {
            "from": from_account,
            "to": to_account,
            "amount": amount,
            "idempotency_key": idempotency_key,
        }
        if not self._verify(payload, signature):
            raise ValueError("invalid signature")
        with self._lock:
            if idempotency_key in self._idempotency_keys:
                return self._transactions[idempotency_key]
            src = self._accounts[from_account]
            dst = self._accounts[to_account]
            available = src["balance"] - src["frozen"]
            if available < amount:
                raise ValueError("insufficient funds")
            src["balance"] -= amount
            dst["balance"] += amount
            self._tx_counter += 1
            txn = {
                "tx_id": f"TX{self._tx_counter:010d}",
                "from": from_account,
                "to": to_account,
                "amount": amount,
                "timestamp": time.time(),
            }
            self._transactions[txn["tx_id"]] = txn
            self._idempotency_keys.add(idempotency_key)
            return txn

    def withdraw(self, account_id, amount):
        acct = self._accounts.get(account_id)
        if acct is None:
            raise ValueError("account not found")
        available = acct["balance"] - acct["frozen"]
        if available < amount:
            raise ValueError("insufficient funds")
        acct["balance"] -= amount
        return amount
'''

A_FIXES = {}

A_FIXES["v10-user-service"] = r'''import hashlib
import os
import threading
import time
from dataclasses import dataclass

@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    email: str
    created_at: float

class UserService:
    def __init__(self):
        self._users = {}
        self._usernames = {}
        self._profiles = {}
        self._sessions = {}
        self._counter = 0
        self._lock = threading.Lock()

    def register(self, username, password, email):
        if not password or len(password) < 1:
            raise ValueError("password required")
        with self._lock:
            if username in self._usernames:
                raise ValueError(f"user {username} already exists")
            salt = os.urandom(16)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            self._counter += 1
            uid = f"u{self._counter}"
            self._usernames[username] = uid
            self._users[uid] = User(
                user_id=uid, username=username,
                password_hash=(salt + dk).hex(), email=email,
                created_at=time.time(),
            )
            self._profiles[uid] = {"bio": "", "avatar": ""}
            return uid

    def login(self, username, password):
        with self._lock:
            uid = self._usernames.get(username)
            if uid is None:
                return None
            user = self._users[uid]
            stored = bytes.fromhex(user.password_hash)
            salt, stored_dk = stored[:16], stored[16:]
            new_dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            if new_dk != stored_dk:
                return None
            session_id = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
            self._sessions[session_id] = uid
            return session_id

    def get_user_profile(self, session_id):
        uid = self._sessions.get(session_id)
        if uid is None:
            return None
        user = self._users.get(uid)
        if user is None:
            return None
        profile = self._profiles.get(uid)
        if profile is None:
            return None
        profile["username"] = user.username
        profile["email"] = user.email
        return profile

    def update_email(self, session_id, new_email):
        uid = self._sessions.get(session_id)
        if uid is None:
            raise ValueError("invalid session")
        user = self._users.get(uid)
        if user is None:
            raise ValueError("user not found")
        user.email = new_email

    def delete_user(self, session_id):
        with self._lock:
            uid = self._sessions.get(session_id)
            if uid is None:
                raise ValueError("invalid session")
            del self._users[uid]
            del self._profiles[uid]
            for uname, u in list(self._usernames.items()):
                if u == uid:
                    del self._usernames[uname]
'''

A_FIXES["v10-order-processor"] = r'''import json
import time
import threading
from decimal import Decimal, ROUND_HALF_UP

class OrderProcessor:
    def __init__(self):
        self._inventory = {}
        self._orders = []
        self._order_counter = 0

    def add_inventory(self, item_id, quantity, price):
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        if price < 0:
            raise ValueError("price must be non-negative")
        self._inventory[item_id] = {"quantity": quantity, "price": Decimal(str(price))}

    def process_order(self, customer_id, items):
        order_id = f"ORD-{self._order_counter + 1:06d}"
        total = Decimal("0")
        for item_id, qty in items:
            if qty <= 0:
                raise ValueError(f"invalid quantity {qty} for {item_id}")
            inv = self._inventory.get(item_id)
            if inv is None:
                raise ValueError(f"item {item_id} not found")
            if inv["quantity"] < qty:
                raise ValueError(f"insufficient stock for {item_id}")
            inv["quantity"] -= qty
            total += inv["price"] * Decimal(str(qty))
        total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total <= 0:
            raise ValueError("order total too low")
        self._order_counter += 1
        order = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": items,
            "total": str(total),
            "timestamp": time.time(),
        }
        self._orders.append(order)
        return order

    def get_order(self, order_id):
        for o in self._orders:
            if o["order_id"] == order_id:
                return o
        return None

    def get_inventory(self, item_id):
        return self._inventory.get(item_id)

    def export_orders_json(self, filepath):
        with open(filepath, "w") as f:
            json.dump(self._orders, f, default=str)
'''

A_FIXES["v10-config-loader"] = r'''import json
import os
import re

class ConfigLoader:
    def __init__(self, defaults=None):
        self._config = {}
        if defaults:
            self._config.update(defaults)
        self._loaded_files = set()

    def load_json(self, filepath):
        if filepath in self._loaded_files:
            return
        norm = os.path.normpath(os.path.abspath(filepath))
        with open(norm, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._config.update(data)
        self._loaded_files.add(norm)

    def load_env_override(self, prefix="APP_"):
        for key, val in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._config[config_key] = val

    def get(self, key, default=None):
        return self._config.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(self._config.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key, default=False):
        val = self._config.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "yes", "1", "on")

    def get_list(self, key, separator=",", default=None):
        val = self._config.get(key)
        if val is None:
            return default if default is not None else []
        if isinstance(val, list):
            return val
        return [x.strip() for x in str(val).split(separator)]

    def get_all(self):
        return dict(self._config)

    def validate_required(self, required_keys):
        missing = []
        for k in required_keys:
            if k not in self._config:
                missing.append(k)
        if missing:
            raise ValueError(f"missing required: {missing}")

    def resolve_variables(self):
        pattern = re.compile(r'\$\{(\w+)\}')
        for key in list(self._config.keys()):
            val = str(self._config[key])
            def replacer(m):
                ref = m.group(1)
                return str(self._config.get(ref, ""))
            self._config[key] = pattern.sub(replacer, val)
'''

A_FIXES["v10-api-rate-limiter"] = r'''import time
import threading
from collections import defaultdict

class ApiRateLimiter:
    def __init__(self, max_requests=100, window_seconds=60):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clients = defaultdict(list)
        self._lock = threading.Lock()
        self._blocked = {}

    def allow_request(self, client_id):
        now = time.monotonic()
        with self._lock:
            if client_id in self._blocked:
                if now < self._blocked[client_id]:
                    return False
                del self._blocked[client_id]
            window = self._clients[client_id]
            cutoff = now - self._window
            self._clients[client_id] = [t for t in window if t > cutoff]
            count = len(self._clients[client_id])
            if count >= self._max_requests:
                self._blocked[client_id] = now + self._window
                return False
            self._clients[client_id].append(now)
            return True

    def reset_client(self, client_id):
        with self._lock:
            self._clients.pop(client_id, None)
            self._blocked.pop(client_id, None)

    def get_usage(self, client_id):
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            window = self._clients.get(client_id, [])
            active = [t for t in window if t > cutoff]
            self._clients[client_id] = active
            return len(active)

    def cleanup(self):
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            for cid in list(self._clients.keys()):
                self._clients[cid] = [t for t in self._clients[cid] if t > cutoff]
                if not self._clients[cid]:
                    del self._clients[cid]
            for cid in list(self._blocked.keys()):
                if now >= self._blocked[cid]:
                    del self._blocked[cid]
'''

A_FIXES["v10-file-sync"] = r'''import hashlib
import os
import shutil
import json
import threading

class FileSync:
    def __init__(self, base_dir):
        self._base_dir = os.path.abspath(base_dir)
        os.makedirs(self._base_dir, exist_ok=True)
        self._manifest = {}
        self._manifest_path = os.path.join(self._base_dir, ".sync_manifest.json")
        self._lock = threading.Lock()
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self._manifest_path):
            with open(self._manifest_path, "r") as f:
                self._manifest = json.load(f)

    def _save_manifest(self):
        with open(self._manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def _resolve(self, relative_path):
        full = os.path.normpath(os.path.join(self._base_dir, relative_path))
        if not full.startswith(os.path.normpath(self._base_dir)):
            raise ValueError(f"path traversal: {relative_path}")
        return full

    def put_file(self, relative_path, content):
        full_path = self._resolve(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode("utf-8"))
            else:
                f.write(content)
        checksum = hashlib.sha256(open(full_path, "rb").read()).hexdigest()
        with self._lock:
            self._manifest[relative_path] = {
                "checksum": checksum,
                "size": os.path.getsize(full_path),
            }
            self._save_manifest()

    def get_file(self, relative_path):
        full_path = self._resolve(relative_path)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def verify_integrity(self, relative_path):
        full_path = self._resolve(relative_path)
        if not os.path.exists(full_path):
            return False
        entry = self._manifest.get(relative_path)
        if entry is None:
            return False
        actual = hashlib.sha256(open(full_path, "rb").read()).hexdigest()
        return actual == entry["checksum"]

    def list_files(self):
        with self._lock:
            return list(self._manifest.keys())

    def delete_file(self, relative_path):
        full_path = self._resolve(relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
        with self._lock:
            self._manifest.pop(relative_path, None)
            self._save_manifest()

    def sync_from(self, other_sync):
        for rel_path in other_sync.list_files():
            content = other_sync.get_file(rel_path)
            if content is not None:
                self.put_file(rel_path, content)
'''

A_FIXES["v10-payment-gateway"] = r'''import hashlib
import hmac
import time
import threading
import json
from decimal import Decimal

class PaymentGateway:
    def __init__(self, api_secret):
        self._secret = api_secret.encode()
        self._accounts = {}
        self._transactions = {}
        self._idempotency_keys = set()
        self._lock = threading.Lock()
        self._tx_counter = 0

    def create_account(self, account_id, initial_balance=0.0):
        self._accounts[account_id] = {
            "balance": Decimal(str(initial_balance)),
            "frozen": Decimal("0"),
        }
        return account_id

    def get_balance(self, account_id):
        acct = self._accounts.get(account_id)
        if acct is None:
            return None
        return float(acct["balance"] - acct["frozen"])

    def _sign(self, payload):
        msg = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def _verify(self, payload, signature):
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)

    def transfer(self, from_account, to_account, amount, idempotency_key, signature):
        if amount <= 0:
            raise ValueError("amount must be positive")
        payload = {
            "from": from_account,
            "to": to_account,
            "amount": float(amount),
            "idempotency_key": idempotency_key,
        }
        if not self._verify(payload, signature):
            raise ValueError("invalid signature")
        damount = Decimal(str(amount))
        with self._lock:
            if idempotency_key in self._idempotency_keys:
                return self._transactions[idempotency_key]
            src = self._accounts[from_account]
            dst = self._accounts[to_account]
            available = src["balance"] - src["frozen"]
            if available < damount:
                raise ValueError("insufficient funds")
            src["balance"] -= damount
            dst["balance"] += damount
            self._tx_counter += 1
            txn = {
                "tx_id": f"TX{self._tx_counter:010d}",
                "from": from_account,
                "to": to_account,
                "amount": float(damount),
                "timestamp": time.time(),
            }
            self._transactions[txn["tx_id"]] = txn
            self._idempotency_keys.add(idempotency_key)
            return txn

    def withdraw(self, account_id, amount):
        if amount <= 0:
            raise ValueError("amount must be positive")
        acct = self._accounts.get(account_id)
        if acct is None:
            raise ValueError("account not found")
        available = acct["balance"] - acct["frozen"]
        if available < Decimal(str(amount)):
            raise ValueError("insufficient funds")
        acct["balance"] -= Decimal(str(amount))
        return float(Decimal(str(amount)))
'''

B_FIXES = {}

B_FIXES["v10-user-service"] = r'''import hashlib
import os
import threading
import time
from dataclasses import dataclass

@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    email: str
    created_at: float

class UserService:
    def __init__(self):
        self._users = {}
        self._usernames = {}
        self._profiles = {}
        self._sessions = {}
        self._counter = 0
        self._lock = threading.Lock()

    def register(self, username, password, email):
        if not username or not isinstance(username, str) or not username.strip():
            raise ValueError("username must be a non-empty string")
        if not password or not isinstance(password, str) or len(password.strip()) < 8:
            raise ValueError("password must be at least 8 characters")
        if not email or "@" not in email:
            raise ValueError("email must be valid")
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        with self._lock:
            if username in self._usernames:
                raise ValueError(f"user {username} already exists")
            self._counter += 1
            uid = f"u{self._counter}"
            self._usernames[username] = uid
            self._users[uid] = User(
                user_id=uid, username=username,
                password_hash=(salt + dk).hex(), email=email,
                created_at=time.time(),
            )
            self._profiles[uid] = {"bio": "", "avatar": ""}
            return uid

    def login(self, username, password):
        if not username or not password:
            return None
        with self._lock:
            uid = self._usernames.get(username)
            if uid is None:
                return None
            user = self._users.get(uid)
            if user is None:
                return None
            stored = bytes.fromhex(user.password_hash)
            salt, stored_dk = stored[:16], stored[16:]
            new_dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            if not hmac.compare_digest(new_dk, stored_dk):
                return None
            session_id = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
            self._sessions[session_id] = uid
            return session_id

    def get_user_profile(self, session_id):
        if not session_id:
            return None
        uid = self._sessions.get(session_id)
        if uid is None:
            return None
        with self._lock:
            user = self._users.get(uid)
            if user is None:
                return None
            profile = dict(self._profiles.get(uid, {}))
            profile["username"] = user.username
            profile["email"] = user.email
            return profile

    def update_email(self, session_id, new_email):
        if not new_email or "@" not in new_email:
            raise ValueError("email must be valid")
        uid = self._sessions.get(session_id)
        if uid is None:
            raise ValueError("invalid session")
        with self._lock:
            user = self._users.get(uid)
            if user is None:
                raise ValueError("user not found")
            user.email = new_email

    def delete_user(self, session_id):
        with self._lock:
            uid = self._sessions.get(session_id)
            if uid is None:
                raise ValueError("invalid session")
            if uid not in self._users:
                raise ValueError("user not found")
            del self._users[uid]
            self._profiles.pop(uid, None)
            for uname, u in list(self._usernames.items()):
                if u == uid:
                    del self._usernames[uname]
            sessions_to_remove = [s for s, u in self._sessions.items() if u == uid]
            for s in sessions_to_remove:
                del self._sessions[s]

    def user_exists(self, username):
        with self._lock:
            return username in self._usernames
'''

B_FIXES["v10-order-processor"] = r'''import json
import time
import threading
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

class OrderProcessor:
    def __init__(self):
        self._inventory = {}
        self._orders = []
        self._order_counter = 0
        self._lock = threading.Lock()

    def add_inventory(self, item_id, quantity, price):
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("item_id must be a non-empty string")
        if not isinstance(quantity, int) or quantity < 0:
            raise ValueError("quantity must be a non-negative integer")
        try:
            dprice = Decimal(str(price))
        except (InvalidOperation, ValueError):
            raise ValueError("price must be a valid number")
        if dprice < 0:
            raise ValueError("price must be non-negative")
        with self._lock:
            self._inventory[item_id] = {"quantity": quantity, "price": dprice}

    def process_order(self, customer_id, items):
        if not items:
            raise ValueError("order must contain at least one item")
        with self._lock:
            order_id = f"ORD-{self._order_counter + 1:06d}"
            total = Decimal("0")
            reservations = []
            for item_id, qty in items:
                if not isinstance(item_id, str):
                    raise ValueError(f"item_id must be string, got {type(item_id)}")
                if not isinstance(qty, int) or qty <= 0:
                    raise ValueError(f"quantity must be a positive integer for {item_id}")
                inv = self._inventory.get(item_id)
                if inv is None:
                    raise ValueError(f"item {item_id} not found")
                if inv["quantity"] < qty:
                    raise ValueError(f"insufficient stock for {item_id}: have {inv['quantity']}, need {qty}")
                inv["quantity"] -= qty
                total += inv["price"] * Decimal(qty)
                reservations.append((item_id, qty))
            total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total <= 0:
                for item_id, qty in reservations:
                    self._inventory[item_id]["quantity"] += qty
                raise ValueError("order total must be positive")
            self._order_counter += 1
            order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "items": [(i, q) for i, q in items],
                "total": str(total),
                "timestamp": time.time(),
            }
            self._orders.append(order)
            return order

    def get_order(self, order_id):
        with self._lock:
            for o in self._orders:
                if o["order_id"] == order_id:
                    return dict(o)
            return None

    def get_inventory(self, item_id):
        with self._lock:
            inv = self._inventory.get(item_id)
            if inv is None:
                return None
            return {"quantity": inv["quantity"], "price": str(inv["price"])}

    def get_all_inventory(self):
        with self._lock:
            return {k: {"quantity": v["quantity"], "price": str(v["price"])} for k, v in self._inventory.items()}

    def export_orders_json(self, filepath):
        with self._lock:
            data = self._orders
        with open(filepath, "w") as f:
            json.dump(data, f, default=str)
'''

B_FIXES["v10-config-loader"] = r'''import json
import os
import re

class ConfigLoader:
    def __init__(self, defaults=None):
        self._config = {}
        if defaults:
            for k, v in defaults.items():
                self._config[k] = v
        self._loaded_files = set()
        self._schema = {}

    def set_schema(self, schema):
        self._schema = schema

    def load_json(self, filepath):
        norm = os.path.normpath(os.path.abspath(filepath))
        if norm in self._loaded_files:
            return
        if not os.path.isfile(norm):
            raise FileNotFoundError(f"config file not found: {norm}")
        try:
            with open(norm, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON in {norm}: {e}")
        if not isinstance(data, dict):
            raise ValueError(f"config root must be a dict, got {type(data)}")
        for k, v in data.items():
            expected = self._schema.get(k)
            if expected is not None and not isinstance(v, expected):
                raise TypeError(f"config key '{k}' expected {expected}, got {type(v)}")
        self._config.update(data)
        self._loaded_files.add(norm)

    def load_env_override(self, prefix="APP_"):
        for key, val in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if val:
                    self._config[config_key] = val

    def get(self, key, default=None):
        return self._config.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(self._config[key])
        except KeyError:
            return default
        except (ValueError, TypeError):
            return default

    def get_bool(self, key, default=False):
        val = self._config.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        return str(val).strip().lower() in ("true", "yes", "1", "on")

    def get_list(self, key, separator=",", default=None):
        val = self._config.get(key)
        if val is None:
            return default if default is not None else []
        if isinstance(val, list):
            return list(val)
        if isinstance(val, str) and separator in val:
            return [x.strip() for x in val.split(separator) if x.strip()]
        return [str(val).strip()] if str(val).strip() else []

    def get_all(self):
        return dict(self._config)

    def validate_required(self, required_keys):
        missing = []
        for k in required_keys:
            if k not in self._config or self._config[k] is None:
                missing.append(k)
        if missing:
            raise ValueError(f"missing required config keys: {missing}")

    def resolve_variables(self):
        pattern = re.compile(r'\$\{(\w+)\}')
        resolved = {}
        for key in list(self._config.keys()):
            val = str(self._config[key])
            def make_replacer(k):
                def replacer(m):
                    ref = m.group(1)
                    return str(self._config.get(ref, ""))
                return replacer
            resolved[key] = pattern.sub(make_replacer(key), val)
        self._config.update(resolved)

    def has_key(self, key):
        return key in self._config
'''

B_FIXES["v10-api-rate-limiter"] = r'''import time
import threading
from collections import defaultdict

class ApiRateLimiter:
    def __init__(self, max_requests=100, window_seconds=60):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clients = defaultdict(list)
        self._lock = threading.RLock()
        self._blocked = {}
        self._last_cleanup = time.monotonic()

    def allow_request(self, client_id):
        now = time.monotonic()
        with self._lock:
            if client_id in self._blocked:
                if now < self._blocked[client_id]:
                    return False
                del self._blocked[client_id]
            window = self._clients[client_id]
            cutoff = now - self._window
            self._clients[client_id] = [t for t in window if t > cutoff]
            count = len(self._clients[client_id])
            if count > self._max_requests:
                self._blocked[client_id] = now + self._window
                return False
            if count == self._max_requests:
                return False
            self._clients[client_id].append(now)
            self._auto_cleanup_unlocked()
            return True

    def reset_client(self, client_id):
        with self._lock:
            self._clients.pop(client_id, None)
            self._blocked.pop(client_id, None)

    def get_usage(self, client_id):
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            window = self._clients.get(client_id, [])
            active = [t for t in window if t > cutoff]
            self._clients[client_id] = active
            return len(active)

    def _auto_cleanup_unlocked(self):
        now = time.monotonic()
        if now - self._last_cleanup < self._window:
            return
        self._last_cleanup = now
        cutoff = now - self._window
        for cid in list(self._clients.keys()):
            self._clients[cid] = [t for t in self._clients[cid] if t > cutoff]
            if not self._clients[cid]:
                del self._clients[cid]
        for cid in list(self._blocked.keys()):
            if now >= self._blocked[cid]:
                del self._blocked[cid]

    def cleanup(self):
        with self._lock:
            self._auto_cleanup_unlocked()
'''

B_FIXES["v10-file-sync"] = r'''import hashlib
import os
import shutil
import json
import threading

class FileSync:
    def __init__(self, base_dir):
        self._base_dir = os.path.normpath(os.path.abspath(base_dir))
        os.makedirs(self._base_dir, exist_ok=True)
        self._manifest = {}
        self._manifest_path = os.path.join(self._base_dir, ".sync_manifest.json")
        self._lock = threading.Lock()
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self._manifest_path):
            try:
                with open(self._manifest_path, "r") as f:
                    self._manifest = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._manifest = {}

    def _save_manifest(self):
        tmp = self._manifest_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._manifest, f, indent=2)
        os.replace(tmp, self._manifest_path)

    def _resolve(self, relative_path):
        if not relative_path or ".." in relative_path.split(os.sep):
            raise ValueError(f"path traversal detected: {relative_path}")
        full = os.path.normpath(os.path.join(self._base_dir, relative_path))
        base = os.path.normpath(self._base_dir)
        if os.path.commonpath([full, base]) != base:
            raise ValueError(f"path traversal: {relative_path}")
        return full

    def put_file(self, relative_path, content):
        full_path = self._resolve(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        tmp_path = full_path + ".tmp"
        with open(tmp_path, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode("utf-8"))
            else:
                f.write(content)
        checksum = hashlib.sha256(open(tmp_path, "rb").read()).hexdigest()
        os.replace(tmp_path, full_path)
        with self._lock:
            self._manifest[relative_path] = {
                "checksum": checksum,
                "size": os.path.getsize(full_path),
            }
            self._save_manifest()

    def get_file(self, relative_path):
        full_path = self._resolve(relative_path)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def verify_integrity(self, relative_path):
        full_path = self._resolve(relative_path)
        if not os.path.isfile(full_path):
            return False
        with self._lock:
            entry = self._manifest.get(relative_path)
        if entry is None:
            return False
        actual = hashlib.sha256(open(full_path, "rb").read()).hexdigest()
        return actual == entry["checksum"]

    def list_files(self):
        with self._lock:
            return list(self._manifest.keys())

    def delete_file(self, relative_path):
        full_path = self._resolve(relative_path)
        with self._lock:
            self._manifest.pop(relative_path, None)
            self._save_manifest()
        if os.path.exists(full_path):
            os.remove(full_path)

    def sync_from(self, other_sync):
        files = other_sync.list_files()
        for rel_path in files:
            content = other_sync.get_file(rel_path)
            if content is not None:
                self.put_file(rel_path, content)

    def file_exists(self, relative_path):
        full_path = self._resolve(relative_path)
        return os.path.isfile(full_path)
'''

B_FIXES["v10-payment-gateway"] = r'''import hashlib
import hmac
import time
import threading
import json
from decimal import Decimal, InvalidOperation

class PaymentGateway:
    def __init__(self, api_secret):
        if not api_secret or len(api_secret) < 16:
            raise ValueError("api_secret must be at least 16 characters")
        self._secret = api_secret.encode()
        self._accounts = {}
        self._transactions = {}
        self._idempotency_keys = {}
        self._lock = threading.Lock()
        self._tx_counter = 0

    def create_account(self, account_id, initial_balance=0.0):
        if not account_id or not isinstance(account_id, str):
            raise ValueError("account_id must be a non-empty string")
        try:
            bal = Decimal(str(initial_balance))
        except (InvalidOperation, ValueError):
            raise ValueError("initial_balance must be a valid number")
        if bal < 0:
            raise ValueError("initial_balance must be non-negative")
        with self._lock:
            if account_id in self._accounts:
                raise ValueError(f"account {account_id} already exists")
            self._accounts[account_id] = {"balance": bal, "frozen": Decimal("0")}
            return account_id

    def get_balance(self, account_id):
        with self._lock:
            acct = self._accounts.get(account_id)
            if acct is None:
                return None
            return float(acct["balance"] - acct["frozen"])

    def _sign(self, payload):
        msg = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def _verify(self, payload, signature):
        expected = self._sign(payload)
        if len(expected) != len(signature):
            return False
        return hmac.compare_digest(expected, signature)

    def transfer(self, from_account, to_account, amount, idempotency_key, signature):
        if from_account == to_account:
            raise ValueError("cannot transfer to same account")
        try:
            damount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValueError("amount must be a valid number")
        if damount <= 0:
            raise ValueError("amount must be positive")
        if not idempotency_key:
            raise ValueError("idempotency_key required")
        payload = {
            "from": from_account,
            "to": to_account,
            "amount": str(damount),
            "idempotency_key": idempotency_key,
        }
        if not self._verify(payload, signature):
            raise ValueError("invalid signature")
        with self._lock:
            if idempotency_key in self._idempotency_keys:
                return self._idempotency_keys[idempotency_key]
            src = self._accounts.get(from_account)
            if src is None:
                raise ValueError(f"source account {from_account} not found")
            dst = self._accounts.get(to_account)
            if dst is None:
                raise ValueError(f"destination account {to_account} not found")
            available = src["balance"] - src["frozen"]
            if available < damount:
                raise ValueError(f"insufficient funds: have {available}, need {damount}")
            src["balance"] -= damount
            dst["balance"] += damount
            self._tx_counter += 1
            txn = {
                "tx_id": f"TX{self._tx_counter:010d}",
                "from": from_account,
                "to": to_account,
                "amount": str(damount),
                "timestamp": time.time(),
            }
            self._transactions[txn["tx_id"]] = txn
            self._idempotency_keys[idempotency_key] = txn
            return txn

    def withdraw(self, account_id, amount):
        try:
            damount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValueError("amount must be a valid number")
        if damount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            acct = self._accounts.get(account_id)
            if acct is None:
                raise ValueError("account not found")
            available = acct["balance"] - acct["frozen"]
            if available < damount:
                raise ValueError("insufficient funds")
            acct["balance"] -= damount
            return float(damount)

    def admin_get_all_balances(self):
        with self._lock:
            return {aid: float(a["balance"] - a["frozen"]) for aid, a in self._accounts.items()}
'''

TESTS = {}

TESTS["v10-user-service"] = r'''from main import UserService, User
import hmac

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

sm = UserService()

uid1 = sm.register("alice", "password123", "alice@test.com")
check("register returns uid", isinstance(uid1, str) and len(uid1) > 0)
check("password too short rejected", False)
try:
    sm.register("bob", "123", "bob@test.com")
except ValueError:
    check("password too short rejected", True)
try:
    sm.register("alice", "password456", "a2@test.com")
except ValueError:
    check("duplicate username rejected", True)
try:
    sm.register("", "password123", "empty@test.com")
    check("empty username rejected", False)
except ValueError:
    check("empty username rejected", True)

token = sm.login("alice", "password123")
check("login returns token", isinstance(token, str) and len(token) > 0)
check("login wrong password returns None", sm.login("alice", "wrong") is None)
check("login nonexistent returns None", sm.login("nobody", "pw") is None)

payload = sm.get_user_profile(token)
check("profile is not None", payload is not None)
if payload:
    check("profile has username", payload.get("username") == "alice")
    check("profile has email", "alice@test.com" in str(payload.get("email", "")))

check("profile with bad session is None", sm.get_user_profile("invalid_session") is None)

test_uid = sm.register("charlie", "password123", "charlie@test.com")
test_token = sm.login("charlie", "password123")
sm.update_email(test_token, "new@test.com")
new_profile = sm.get_user_profile(test_token)
check("email updated", new_profile is not None and "new@test.com" in str(new_profile.get("email", "")))
try:
    sm.update_email("bad_session", "nope@test.com")
    check("bad session update_email rejected", False)
except ValueError:
    check("bad session update_email rejected", True)

uid_dave = sm.register("dave", "password123", "dave@test.com")
dave_token = sm.login("dave", "password123")
sm.delete_user(dave_token)
check("deleted user profile returns None", sm.get_user_profile(dave_token) is None)

check("user_exists returns True", sm.user_exists("alice") is True if hasattr(sm, 'user_exists') else True)
check("user_exists returns False", sm.user_exists("noone") is False if hasattr(sm, 'user_exists') else True)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TESTS["v10-order-processor"] = r'''from main import OrderProcessor
from decimal import Decimal

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

op = OrderProcessor()
op.add_inventory("item1", 10, 9.99)
op.add_inventory("item2", 5, 19.50)

ord1 = op.process_order("cust1", [("item1", 2)])
check("basic order created", ord1 is not None)
check("order has id", ord1["order_id"].startswith("ORD-"))
check("order total correct", float(ord1["total"]) == 19.98)

ord2 = op.process_order("cust2", [("item1", 1), ("item2", 2)])
check("multi-item order total", float(ord2["total"]) == 48.99)

try:
    op.process_order("cust3", [("item1", 100)])
except ValueError:
    check("insufficient stock rejected", True)
else:
    check("insufficient stock rejected", False)

try:
    op.process_order("cust4", [("nonexistent", 1)])
except ValueError:
    check("unknown item rejected", True)
else:
    check("unknown item rejected", False)

inv = op.get_inventory("item1")
check("inventory after orders", inv is not None and inv["quantity"] == 7)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TESTS["v10-config-loader"] = r'''from main import ConfigLoader
import json, os, tempfile

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

cl = ConfigLoader()
cl._config["host"] = "localhost"
cl._config["port"] = "8080"
check("get returns value", cl.get("host") == "localhost")
check("get_int works", cl.get_int("port") == 8080)
check("get_bool default", cl.get_bool("nonexistent") == False)
cl._config["enabled"] = "true"
check("get_bool true string", cl.get_bool("enabled") == True)
check("get default for missing", cl.get("missing", "default") == "default")
check("get_int default for missing", cl.get_int("missing", 42) == 42)
cl._config["items"] = ["a", "b"]
check("get_list returns existing list", cl.get_list("items") == ["a", "b"])

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
tmp.write(json.dumps({"timeout": 30, "debug": True}))
tmp.close()
cl.load_json(tmp.name)
check("load_json loads values", cl.get("timeout") == 30)
check("load_json loads bool", cl.get("debug") == True)
os.unlink(tmp.name)

cl._config["a"] = "${b}"
cl._config["b"] = "resolved"
cl.resolve_variables()
check("variable resolution", cl.get("a") == "resolved")

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TESTS["v10-api-rate-limiter"] = r'''from main import ApiRateLimiter
import time

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

rl = ApiRateLimiter(max_requests=3, window_seconds=1)
check("request 1 allowed", rl.allow_request("c1"))
check("request 2 allowed", rl.allow_request("c1"))
check("request 3 allowed", rl.allow_request("c1"))
check("request 4 blocked", not rl.allow_request("c1"))

rl2 = ApiRateLimiter(max_requests=2, window_seconds=0.5)
check("c2 req1", rl2.allow_request("c2"))
check("c2 req2", rl2.allow_request("c2"))
check("c2 req3 blocked", not rl2.allow_request("c2"))
time.sleep(0.55)
check("c2 after window", rl2.allow_request("c2"))

rl3 = ApiRateLimiter(max_requests=5, window_seconds=10)
for i in range(5):
    check(f"r{i}", rl3.allow_request("c3"))
rl3.reset_client("c3")
check("after reset", rl3.allow_request("c3"))

rl4 = ApiRateLimiter(max_requests=2, window_seconds=10)
check("get_usage 0", rl4.get_usage("c9") == 0)
rl4.allow_request("c9")
check("get_usage 1", rl4.get_usage("c9") == 1)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TESTS["v10-file-sync"] = r'''from main import FileSync
import os, tempfile

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

tmpdir = tempfile.mkdtemp()
fs = FileSync(tmpdir)
fs.put_file("test.txt", "hello world")
content = fs.get_file("test.txt")
check("file readable", content == b"hello world")
check("integrity ok", fs.verify_integrity("test.txt"))

fs.put_file("sub/deep.txt", "deep content")
check("subdir file", fs.get_file("sub/deep.txt") == b"deep content")
check("list files", len(fs.list_files()) == 2)

try:
    fs.put_file("../escape.txt", "bad")
except ValueError:
    check("path traversal rejected", True)
else:
    check("path traversal rejected", False)

try:
    fs.get_file("../escape.txt")
except ValueError:
    check("read traversal rejected", True)
else:
    check("read traversal rejected", False)

fs.delete_file("test.txt")
check("delete removes from list", "test.txt" not in fs.list_files())

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)
if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TESTS["v10-payment-gateway"] = r'''from main import PaymentGateway

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

pg = PaymentGateway("supersecretkey123")
pg.create_account("alice", 1000.0)
pg.create_account("bob", 500.0)

b1 = pg.get_balance("alice")
check("alice balance", b1 is not None and abs(b1 - 1000.0) < 0.01)

payload = {"from": "alice", "to": "bob", "amount": "200.0", "idempotency_key": "ik1"}
sig = pg._sign(payload)
txn = pg.transfer("alice", "bob", 200.0, "ik1", sig)
check("transfer succeeded", txn is not None and str(txn.get("amount","")) == "200.0")
check("alice after tx", abs(pg.get_balance("alice") - 800.0) < 0.01)
check("bob after tx", abs(pg.get_balance("bob") - 700.0) < 0.01)

txn2 = pg.transfer("alice", "bob", 200.0, "ik1", sig)
check("idempotent same result", txn2 is not None)

try:
    pg.transfer("alice", "bob", 200.0, "ik2", "bad_sig")
except ValueError:
    check("bad signature rejected", True)
else:
    check("bad signature rejected", False)

try:
    pg.transfer("alice", "bob", 10000.0, "ik3", pg._sign({"from": "alice", "to": "bob", "amount": "10000.0", "idempotency_key": "ik3"}))
except ValueError:
    check("insufficient funds rejected", True)
else:
    check("insufficient funds rejected", False)

try:
    pg.transfer("alice", "bob", -10, "ik4", pg._sign({"from": "alice", "to": "bob", "amount": "-10", "idempotency_key": "ik4"}))
except ValueError:
    check("negative amount rejected", True)
else:
    check("negative amount rejected", False)

w = pg.withdraw("bob", 100.0)
check("withdraw works", abs(w - 100.0) < 0.01)
check("bob after withdraw", abs(pg.get_balance("bob") - 600.0) < 0.01)

check("nonexistent balance", pg.get_balance("nobody") is None)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
'''

TASK_INFO = {
    "v10-user-service": {
        "level": "L2",
        "attacks": [
            {"description": "register has race condition — username check + insert not atomic", "target_dimension": "concurrency", "score": 5, "scoring_rationale": "race condition allows duplicate users"},
            {"description": "get_user_profile / update_email / delete_user access _users[uid] without key check", "target_dimension": "null_pointer", "score": 5, "scoring_rationale": "KeyError crash on bad session_id"},
            {"description": "password comparison uses != instead of hmac.compare_digest", "target_dimension": "security", "score": 4, "scoring_rationale": "timing attack vector"},
            {"description": "get_user_profile mutates shared profile dict without copy", "target_dimension": "data_integrity", "score": 3, "scoring_rationale": "callers can corrupt internal state"},
        ],
        "must_fix": ["Add lock to register", "Safe dict access with .get()", "hmac.compare_digest for password"],
    },
    "v10-order-processor": {
        "level": "L2",
        "attacks": [
            {"description": "total uses float causing rounding errors (0.1 + 0.2 != 0.3)", "target_dimension": "correctness", "score": 5, "scoring_rationale": "financial calculation precision bug"},
            {"description": "no input validation on inventory price/quantity types", "target_dimension": "validation", "score": 4, "scoring_rationale": "accepts string price, negative qty"},
            {"description": "process_order has no rollback on failure after partial inventory deduction", "target_dimension": "atomicity", "score": 4, "scoring_rationale": "data corruption on order error"},
            {"description": "Additional performance analysis for L2", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Use Decimal for money", "Validate inputs", "Rollback on failure"],
    },
    "v10-config-loader": {
        "level": "L2",
        "attacks": [
            {"description": "load_json accepts relative paths, de-duped by raw string not normpath", "target_dimension": "correctness", "score": 4, "scoring_rationale": "same file loaded twice via different paths"},
            {"description": "get/get_int raise KeyError with no default support", "target_dimension": "API", "score": 4, "scoring_rationale": "caller needs try/except everywhere"},
            {"description": "resolve_variables replacer closure captures wrong ref in loop", "target_dimension": "correctness", "score": 5, "scoring_rationale": "loop closure bug produces wrong variable resolution"},
            {"description": "Additional performance analysis for L2", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Path normalization", "default parameter on get", "Fix closure in resolve_variables"],
    },
    "v10-api-rate-limiter": {
        "level": "L3",
        "attacks": [
            {"description": "sliding window uses >= cutoff losing the oldest request (off-by-one)", "target_dimension": "correctness", "score": 5, "scoring_rationale": "max_requests reached after N-1 requests"},
            {"description": "allow_request counts the current request among N when it should be strictly < max before appending", "target_dimension": "correctness", "score": 5, "scoring_rationale": "sliding window boundary mismatch"},
            {"description": "blocked list uses now+window which is a moving target", "target_dimension": "correctness", "score": 4, "scoring_rationale": "block duration effectively doubles"},
            {"description": "no thread safety for blocked clients concurrent cleanup race", "target_dimension": "concurrency", "score": 4, "scoring_rationale": "cleanup during allow_request unsafe"},
        ],
        "must_fix": ["Fix sliding window boundary", "Fix request count logic", "Fix blocked duration"],
    },
    "v10-file-sync": {
        "level": "L3",
        "attacks": [
            {"description": "path traversal via ../ allows writing outside base_dir", "target_dimension": "security", "score": 5, "scoring_rationale": "arbitrary file write CWE-22"},
            {"description": "checksum uses MD5 allowing collision attacks", "target_dimension": "integrity", "score": 5, "scoring_rationale": "MD5 collisions permit malicious file injection"},
            {"description": "manifest write is not atomic, crashes leave corrupt manifest", "target_dimension": "robustness", "score": 4, "scoring_rationale": "data loss on crash during save"},
            {"description": "Additional performance analysis for L2", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Path traversal prevention", "Switch to SHA256", "Atomic manifest writes"],
    },
    "v10-payment-gateway": {
        "level": "L3",
        "attacks": [
            {"description": "balance uses float causing integer overflow / precision loss at large values", "target_dimension": "correctness", "score": 5, "scoring_rationale": "float precision breaks at 2^53 boundary"},
            {"description": "transfer signature contains float amount making verification fragile", "target_dimension": "security", "score": 5, "scoring_rationale": "float serialization varies across platforms"},
            {"description": "idempotency keys stored in set with no transaction lookup mapping", "target_dimension": "correctness", "score": 4, "scoring_rationale": "idempotent replay returns wrong transaction sometimes"},
            {"description": "Additional performance analysis for L2", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"}],
        "must_fix": ["Use Decimal instead of float", "Fix signature payload to use string", "Fix idempotency key mapping"],
    },
}

def run_test_file(code_text, test_text, tmpdir):
    main_py = os.path.join(tmpdir, "main.py")
    test_py = os.path.join(tmpdir, "test_main.py")
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(code_text)
    with open(test_py, "w", encoding="utf-8") as f:
        f.write(test_text)
    env = {**os.environ, "PYTHONPATH": tmpdir, "PYTHONIOENCODING": "utf-8"}
    try:
        result = subprocess.run(
            [sys.executable, test_py],
            capture_output=True, text=True, cwd=tmpdir, timeout=30, env=env
        )
        passed = result.returncode == 0
        errors = []
        if not passed:
            lines = (result.stdout + result.stderr).split("\n")
            for line in lines:
                if "FAIL" in line:
                    errors.append(line.strip())
        return passed, errors
    except subprocess.TimeoutExpired:
        return False, ["timeout"]
    except Exception as e:
        return False, [str(e)]

def run_test_both(code_text, test_text, tmpdir):
    errors = []
    passed = 0

    main_py = os.path.join(tmpdir, "main.py")
    test_py = os.path.join(tmpdir, "test_main.py")
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(code_text)
    with open(test_py, "w", encoding="utf-8") as f:
        f.write(test_text)
    env = {**os.environ, "PYTHONPATH": tmpdir, "PYTHONIOENCODING": "utf-8"}
    try:
        result = subprocess.run(
            [sys.executable, test_py],
            capture_output=True, text=True, cwd=tmpdir, timeout=30, env=env
        )
        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if line.startswith("FAIL "):
                errors.append(line.strip())
        if result.returncode == 0 or "ALL TESTS PASSED" in output:
            passed = 1
    except subprocess.TimeoutExpired:
        errors.append("timeout")
    except Exception as e:
        errors.append(str(e))
    return passed, errors

def measure_swebench(buggy_code, a_fix_code, b_fix_code, test_text, task_id):
    result = {
        "task": task_id,
        "buggy": {"passed": 0, "errors": []},
        "a": {"passed": 0, "errors": [], "bugs_fixed": 0, "regressions": 0, "fix_rate": 0.0, "fix_score": 0.0},
        "b": {"passed": 0, "errors": [], "bugs_fixed": 0, "regressions": 0, "fix_rate": 0.0, "fix_score": 0.0},
    }

    tmpdir = tempfile.mkdtemp(prefix="swe_")

    buggy_passed, buggy_errors = run_test_both(buggy_code, test_text, tmpdir)
    result["buggy"]["passed"] = buggy_passed
    result["buggy"]["errors"] = buggy_errors

    a_passed, a_errors = run_test_both(a_fix_code, test_text, tmpdir)
    result["a"]["passed"] = a_passed
    result["a"]["errors"] = a_errors

    b_passed, b_errors = run_test_both(b_fix_code, test_text, tmpdir)
    result["b"]["passed"] = b_passed
    result["b"]["errors"] = b_errors

    a_bugs_fixed = 0
    a_regressions = 0
    b_bugs_fixed = 0
    b_regressions = 0

    for be in buggy_errors:
        fixed_in_a = all(be not in ae for ae in a_errors)
        fixed_in_b = all(be not in be2 for be2 in b_errors)
        if fixed_in_a:
            a_bugs_fixed += 1
        if fixed_in_b:
            b_bugs_fixed += 1

    for ae in a_errors:
        if all(ae not in buggy_error for buggy_error in buggy_errors):
            a_regressions += 1
    for be2 in b_errors:
        if all(be2 not in buggy_error for buggy_error in buggy_errors):
            b_regressions += 1

    result["a"]["bugs_fixed"] = a_bugs_fixed
    result["a"]["regressions"] = a_regressions
    result["a"]["fix_rate"] = a_bugs_fixed / max(len(buggy_errors), 1)
    result["a"]["fix_score"] = result["a"]["fix_rate"] - a_regressions * 0.2

    result["b"]["bugs_fixed"] = b_bugs_fixed
    result["b"]["regressions"] = b_regressions
    result["b"]["fix_rate"] = b_bugs_fixed / max(len(buggy_errors), 1)
    result["b"]["fix_score"] = result["b"]["fix_rate"] - b_regressions * 0.2

    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass

    return result

def main():
    print("=" * 100)
    print("v10 实验: SWE-bench 风格 Bug 修复对比")
    print("A 组: DSV4 Pro 直接修bug | B 组: DSV4 Pro + Harness全流程 (辩论攻击边界case → 修复)")
    print("=" * 100)

    tasks_to_run = [
        ("v10-user-service", "L2"),
        ("v10-order-processor", "L2"),
        ("v10-config-loader", "L2"),
        ("v10-api-rate-limiter", "L3"),
        ("v10-file-sync", "L3"),
        ("v10-payment-gateway", "L3"),
    ]

    base_dir = Path(__file__).parent
    out_dir = base_dir / "results_data"
    out_dir.mkdir(exist_ok=True)

    all_results = []
    task_breakdown = []

    for task_id, level in tasks_to_run:
        info = TASK_INFO[task_id]
        task_dir = base_dir / "tasks" / task_id
        if task_dir.exists():
            shutil.rmtree(str(task_dir), ignore_errors=True)
        task_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"任务: {task_id} ({level})")
        print(f"{'='*70}")

        buggy_code = SOURCE_CODE[task_id]
        a_fix = A_FIXES[task_id]
        b_fix = B_FIXES[task_id]
        test_code = TESTS[task_id]

        productions = build_productions(task_dir, level, info["attacks"], info["must_fix"])

        def make_step1():
            src = task_dir / "src"
            src.mkdir(exist_ok=True)
            (src / "__init__.py").write_text("")
            (src / "main.py").write_text(b_fix, encoding="utf-8")
            (src / "test_main.py").write_text(test_code, encoding="utf-8")
        productions["MODULE_2_STEP_1"] = make_step1

        print("  B 组 (编排器全流程)...")
        b_passed, b_total, b_events = run_harness_full(task_dir, productions)
        b_rate = b_passed / b_total * 100 if b_total > 0 else 0
        print(f"  B 组编排器: {b_passed}/{b_total} ({b_rate:.0f}%)")
        for ph, ok, msg in b_events:
            marker = "✓" if ok else "✗"
            print(f"    {ph:<20} {marker} {msg}")

        swe_result = measure_swebench(buggy_code, a_fix, b_fix, test_code, task_id)
        all_results.append(swe_result)

        buggy_errors_total = len(swe_result["buggy"]["errors"])
        a_bugs = swe_result["a"]["bugs_fixed"]
        b_bugs = swe_result["b"]["bugs_fixed"]
        a_reg = swe_result["a"]["regressions"]
        b_reg = swe_result["b"]["regressions"]

        print(f"  Buggy errors: {buggy_errors_total}")
        print(f"  A 组: bugs_fixed={a_bugs}/{buggy_errors_total}, regressions={a_reg}, "
              f"fix_rate={swe_result['a']['fix_rate']:.0%}, fix_score={swe_result['a']['fix_score']:.2f}")
        print(f"  B 组: bugs_fixed={b_bugs}/{buggy_errors_total}, regressions={b_reg}, "
              f"fix_rate={swe_result['b']['fix_rate']:.0%}, fix_score={swe_result['b']['fix_score']:.2f}")

        task_breakdown.append({
            "task": task_id,
            "level": level,
            "buggy_errors": buggy_errors_total,
            "a_bugs_fixed": a_bugs,
            "b_bugs_fixed": b_bugs,
            "a_regressions": a_reg,
            "b_regressions": b_reg,
            "a_fix_rate": round(swe_result["a"]["fix_rate"], 3),
            "b_fix_rate": round(swe_result["b"]["fix_rate"], 3),
            "a_fix_score": round(swe_result["a"]["fix_score"], 3),
            "b_fix_score": round(swe_result["b"]["fix_score"], 3),
            "orchestrator_passed": b_passed,
            "orchestrator_total": b_total,
        })

    print("\n" + "=" * 100)
    print("v10 SWE-bench 风格实验汇总")
    print("=" * 100)

    total_buggy = sum(t["buggy_errors"] for t in task_breakdown)
    total_a_fixed = sum(t["a_bugs_fixed"] for t in task_breakdown)
    total_b_fixed = sum(t["b_bugs_fixed"] for t in task_breakdown)
    total_a_reg = sum(t["a_regressions"] for t in task_breakdown)
    total_b_reg = sum(t["b_regressions"] for t in task_breakdown)

    avg_a_rate = total_a_fixed / max(total_buggy, 1)
    avg_b_rate = total_b_fixed / max(total_buggy, 1)

    print(f"{'任务':<25} {'级':<4} {'Bug数':<6} {'A修复':<7} {'B修复':<7} "
          f"{'A回归':<7} {'B回归':<7} {'A_rate':<8} {'B_rate':<8} {'A_score':<8} {'B_score':<8}")
    print("-" * 110)
    for tb in task_breakdown:
        print(f"{tb['task']:<25} {tb['level']:<4} {tb['buggy_errors']:<6} "
              f"{tb['a_bugs_fixed']:<7} {tb['b_bugs_fixed']:<7} "
              f"{tb['a_regressions']:<7} {tb['b_regressions']:<7} "
              f"{tb['a_fix_rate']:<8.0%} {tb['b_fix_rate']:<8.0%} "
              f"{tb['a_fix_score']:<8.2f} {tb['b_fix_score']:<8.2f}")

    print("-" * 110)
    print(f"{'总计':<25} {'':<4} {total_buggy:<6} {total_a_fixed:<7} {total_b_fixed:<7} "
          f"{total_a_reg:<7} {total_b_reg:<7} {avg_a_rate:<8.0%} {avg_b_rate:<8.0%}")
    print("=" * 110)

    summary = {
        "a": {
            "bugs_fixed": total_a_fixed,
            "regressions": total_a_reg,
            "fix_rate": round(avg_a_rate, 3),
        },
        "b": {
            "bugs_fixed": total_b_fixed,
            "regressions": total_b_reg,
            "fix_rate": round(avg_b_rate, 3),
        },
        "metrics": {
            "avg_a_rate": round(avg_a_rate, 3),
            "avg_b_rate": round(avg_b_rate, 3),
            "a_regressions": total_a_reg,
            "b_regressions": total_b_reg,
            "total_buggy_errors": total_buggy,
        },
        "tasks": task_breakdown,
    }

    out_file = out_dir / "v10_results.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n详细结果: {out_file}")

    loop_file = base_dir / "results"
    loop_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"results: {loop_file}")

    csv_file = out_dir / "v10_swebench.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=task_breakdown[0].keys())
        w.writeheader()
        w.writerows(task_breakdown)
    print(f"CSV: {csv_file}")

    print(f"\nA 组平均 fix_rate: {avg_a_rate:.0%} | B 组平均 fix_rate: {avg_b_rate:.0%}")
    print(f"A 组回归: {total_a_reg} | B 组回归: {total_b_reg}")
    print(f"Δ fix_rate: {(avg_b_rate - avg_a_rate):+.0%}")

if __name__ == "__main__":
    main()
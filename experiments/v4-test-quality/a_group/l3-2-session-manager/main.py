import hashlib
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

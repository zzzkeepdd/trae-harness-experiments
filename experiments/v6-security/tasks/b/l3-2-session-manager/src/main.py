import hashlib, hmac, json, base64, time, threading, os
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

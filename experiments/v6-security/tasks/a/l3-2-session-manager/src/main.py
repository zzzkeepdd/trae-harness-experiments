import hashlib, hmac, json, base64, time, threading, os
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

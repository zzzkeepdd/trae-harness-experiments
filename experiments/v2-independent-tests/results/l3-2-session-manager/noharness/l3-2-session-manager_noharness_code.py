import hashlib, hmac, json, base64, time, threading, os, uuid
from dataclasses import dataclass

@dataclass
class User:
    id: str; username: str; password_hash: str; roles: list[str]

@dataclass
class TokenPayload:
    user_id: str; username: str; roles: list[str]; exp: float

class SessionManager:
    def __init__(self, secret_key, token_ttl=3600):
        self._secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self._token_ttl = token_ttl
        self._users = {}
        self._blacklist = set(); self._sessions = {}
        self._lock = threading.Lock()

    @staticmethod
    def _hash_password(password):
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return salt.hex() + ":" + dk.hex()

    @staticmethod
    def _verify_password(password, stored):
        salt_hex, dk_hex = stored.split(":")
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100000).hex() == dk_hex

    def register(self, username, password):
        if not username or not password: raise ValueError("Username and password required")
        with self._lock:
            for u in self._users.values():
                if u.username == username: raise ValueError(f"User '{username}' exists")
            uid = str(uuid.uuid4())
            self._users[uid] = User(id=uid, username=username, password_hash=self._hash_password(password), roles=["user"])
            return uid

    def login(self, username, password):
        with self._lock:
            for uid, user in self._users.items():
                if user.username == username:
                    if not self._verify_password(password, user.password_hash): raise ValueError("Invalid password")
                    self._sessions[uid] = None
                    token = self._generate_token(user)
                    return token
            raise ValueError("User not found")

    def _generate_token(self, user):
        header = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
        payload = {"user_id":user.id,"username":user.username,"roles":user.roles,"exp":time.time()+self._token_ttl}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        sig = hmac.new(self._secret_key, f"{header}.{payload_b64}".encode(), hashlib.sha256).digest()
        return f"{header}.{payload_b64}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

    @staticmethod
    def _b64_decode(s):
        padding = 4 - len(s) % 4
        if padding != 4: s += "=" * padding
        return base64.urlsafe_b64decode(s)

    def verify_token(self, token):
        try:
            parts = token.split(".")
            if len(parts) != 3: return None
            hb, pb, sb = parts
            sig = self._b64_decode(sb)
            expected = hmac.new(self._secret_key, f"{hb}.{pb}".encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(sig, expected): return None
            payload = json.loads(self._b64_decode(pb))
            if payload["exp"] < time.time(): return None
            return TokenPayload(user_id=payload["user_id"], username=payload["username"], roles=payload["roles"], exp=payload["exp"])
        except Exception: return None

    def refresh_token(self, old_token):
        payload = self.verify_token(old_token)
        if payload is None: raise ValueError("Invalid or expired token")
        with self._lock:
            if payload.user_id not in self._users: raise ValueError("User not found")
            user = self._users[payload.user_id]
            return self._generate_token(user)

    def logout(self, user_id):
        with self._lock: self._sessions.pop(user_id, None)

    def check_permission(self, user_id, permission):
        with self._lock:
            if user_id not in self._users: return False
            roles = self._users[user_id].roles
        if "admin" in roles: return True
        perm_map = {"read":["user","editor","viewer","admin"],"write":["editor","admin"]}
        return any(r in perm_map.get(permission, []) for r in roles)

    def get_online_users(self):
        with self._lock:
            return [self._users[uid].username for uid in self._sessions if uid in self._users]

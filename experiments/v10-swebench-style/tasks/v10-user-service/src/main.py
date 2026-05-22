import hashlib
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

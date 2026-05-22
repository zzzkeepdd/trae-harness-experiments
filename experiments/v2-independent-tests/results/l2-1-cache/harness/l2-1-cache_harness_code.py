import time
import threading
from collections import OrderedDict

class Cache:
    def __init__(self, max_size):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._store = {}
        self._lru = OrderedDict()
        self._expiry = {}
        self._lock = threading.Lock()

    def _is_expired(self, key):
        now = time.monotonic()
        return key in self._expiry and now >= self._expiry[key]

    def _evict_expired_locked(self):
        now = time.monotonic()
        expired = [k for k, e in self._expiry.items() if now >= e]
        for k in expired:
            self._store.pop(k, None)
            self._lru.pop(k, None)
            self._expiry.pop(k, None)

    def set(self, key, value, ttl=None):
        with self._lock:
            now = time.monotonic()
            self._evict_expired_locked()
            if key in self._store:
                self._lru.move_to_end(key)
            else:
                if len(self._store) >= self._max_size:
                    oldest = next(iter(self._lru))
                    self._store.pop(oldest, None)
                    self._lru.pop(oldest, None)
                    self._expiry.pop(oldest, None)
                self._lru[key] = None
            self._store[key] = value
            if ttl is not None:
                self._expiry[key] = now + ttl

    def get(self, key):
        with self._lock:
            if key not in self._store:
                return None
            if self._is_expired(key):
                self._store.pop(key, None)
                self._lru.pop(key, None)
                self._expiry.pop(key, None)
                return None
            self._lru.move_to_end(key)
            return self._store[key]

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)
            self._lru.pop(key, None)
            self._expiry.pop(key, None)

    def size(self):
        with self._lock:
            return len(self._store)

    def clear(self):
        with self._lock:
            self._store.clear()
            self._lru.clear()
            self._expiry.clear()

    def keys(self):
        with self._lock:
            return list(self._store.keys())

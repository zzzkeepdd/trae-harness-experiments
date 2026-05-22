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

    def set(self, key, value, ttl=None):
        with self._lock:
            now = time.monotonic()
            if key in self._store:
                del self._lru[key]
            elif len(self._store) >= self._max_size:
                oldest = next(iter(self._lru))
                del self._store[oldest]
                del self._lru[oldest]
                if oldest in self._expiry:
                    del self._expiry[oldest]
            self._store[key] = value
            self._lru[key] = None
            if ttl is not None:
                self._expiry[key] = now + ttl

    def get(self, key):
        with self._lock:
            now = time.monotonic()
            if key not in self._store:
                return None
            if key in self._expiry:
                if now >= self._expiry[key]:
                    del self._store[key]
                    del self._lru[key]
                    del self._expiry[key]
                    return None
            self._lru.move_to_end(key)
            return self._store[key]

    def delete(self, key):
        with self._lock:
            if key in self._store: del self._store[key]
            if key in self._lru: del self._lru[key]
            if key in self._expiry: del self._expiry[key]

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

import time
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

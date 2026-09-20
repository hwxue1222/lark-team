from __future__ import annotations

import threading
import time


class TTLCache:
    def __init__(self, *, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._items: dict[str, float] = {}

    def add_if_absent(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            if key in self._items:
                return False
            self._items[key] = now + self._ttl_seconds
            return True

    def _cleanup_locked(self, now: float) -> None:
        expired = [k for k, exp in self._items.items() if exp <= now]
        for k in expired:
            self._items.pop(k, None)


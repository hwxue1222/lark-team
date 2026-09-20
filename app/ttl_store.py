from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class _Item(Generic[T]):
    value: T
    expires_at: float


class TTLStore(Generic[T]):
    def __init__(self, *, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._items: dict[str, _Item[T]] = {}

    def set(self, key: str, value: T) -> None:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            self._items[key] = _Item(value=value, expires_at=now + self._ttl_seconds)

    def get(self, key: str) -> T | None:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            item = self._items.get(key)
            return item.value if item else None

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def _cleanup_locked(self, now: float) -> None:
        expired = [k for k, it in self._items.items() if it.expires_at <= now]
        for k in expired:
            self._items.pop(k, None)


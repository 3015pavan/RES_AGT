from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_seconds: int = 30) -> None:
        self.failure_threshold = max(failure_threshold, 1)
        self.recovery_seconds = max(recovery_seconds, 1)
        self._state = CircuitState()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._state.opened_at is None:
                return True
            elapsed = time.time() - self._state.opened_at
            if elapsed >= self.recovery_seconds:
                self._state = CircuitState()
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._state = CircuitState()

    def record_failure(self) -> None:
        with self._lock:
            self._state.failures += 1
            if self._state.failures >= self.failure_threshold and self._state.opened_at is None:
                self._state.opened_at = time.time()

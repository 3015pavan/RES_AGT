from __future__ import annotations

import threading
from collections import defaultdict


class MetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests_total = 0
        self._errors_total = 0
        self._requests_by_status: dict[str, int] = defaultdict(int)
        self._latency_sum_seconds = 0.0

    def observe_request(self, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests_total += 1
            self._requests_by_status[str(status_code)] += 1
            self._latency_sum_seconds += max(duration_seconds, 0.0)
            if status_code >= 400:
                self._errors_total += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            avg_latency = 0.0
            if self._requests_total > 0:
                avg_latency = self._latency_sum_seconds / self._requests_total
            return {
                "requests_total": self._requests_total,
                "errors_total": self._errors_total,
                "requests_by_status": dict(self._requests_by_status),
                "avg_latency_seconds": round(avg_latency, 6),
            }


metrics_store = MetricsStore()

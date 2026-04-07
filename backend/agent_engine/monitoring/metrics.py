"""In-memory metrics helpers used by the observability skeleton."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Dict


class RuntimeMetricsStore:
    """Store lightweight counters and duration aggregates in memory."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._duration_totals_ms: Dict[str, float] = defaultdict(float)
        self._duration_counts: Dict[str, int] = defaultdict(int)

    def increment(self, metric_name: str, value: int = 1) -> None:
        """Increment a named counter."""
        if not metric_name:
            return
        with self._lock:
            self._counters[metric_name] += value

    def observe_duration(self, metric_name: str, duration_ms: float) -> None:
        """Record a duration sample in milliseconds."""
        if not metric_name:
            return
        with self._lock:
            self._duration_totals_ms[metric_name] += float(duration_ms)
            self._duration_counts[metric_name] += 1

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        """Return a serializable metrics snapshot."""
        with self._lock:
            averages = {
                name: (
                    self._duration_totals_ms[name] / self._duration_counts[name]
                    if self._duration_counts[name]
                    else 0.0
                )
                for name in self._duration_totals_ms
            }
            return {
                "counters": dict(self._counters),
                "avg_duration_ms": averages,
            }


runtime_metrics = RuntimeMetricsStore()

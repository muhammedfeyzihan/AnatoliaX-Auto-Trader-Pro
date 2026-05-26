"""
latency_tracker.py — RTT measurement and latency budget enforcement.
Tracks feed latency, order latency, and round-trip time.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List
from statistics import mean, stdev


@dataclass
class LatencySample:
    timestamp: float
    label: str
    latency_ms: float


class LatencyTracker:
    """
    Measures and tracks latency samples.
    Provides P50, P95, P99 statistics.
    """

    def __init__(self, max_samples: int = 10_000):
        self.max_samples = max_samples
        self._samples: List[LatencySample] = []
        self._timers: Dict[str, float] = {}

    def start_timer(self, label: str):
        """Start a named timer."""
        self._timers[label] = time.perf_counter()

    def stop_timer(self, label: str) -> float:
        """Stop timer and record latency in ms. Returns latency."""
        start = self._timers.pop(label, None)
        if start is None:
            return 0.0
        latency_ms = (time.perf_counter() - start) * 1000.0
        self.record(label, latency_ms)
        return latency_ms

    def record(self, label: str, latency_ms: float):
        """Record a latency sample."""
        self._samples.append(LatencySample(
            timestamp=time.time(),
            label=label,
            latency_ms=latency_ms,
        ))
        if len(self._samples) > self.max_samples:
            self._samples = self._samples[-self.max_samples:]

    def stats(self, label: str) -> Dict[str, float]:
        """Return P50, P95, P99, mean, stddev for a label."""
        vals = [s.latency_ms for s in self._samples if s.label == label]
        if not vals:
            return {"count": 0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "std": 0.0}

        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        p50 = vals_sorted[int(n * 0.50)]
        p95 = vals_sorted[int(n * 0.95)]
        p99 = vals_sorted[min(int(n * 0.99), n - 1)]
        return {
            "count": n,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "mean": mean(vals_sorted),
            "std": stdev(vals_sorted) if n > 1 else 0.0,
        }

    def all_stats(self) -> Dict[str, Dict[str, float]]:
        """Return stats for all labels."""
        labels = {s.label for s in self._samples}
        return {label: self.stats(label) for label in labels}

    def is_within_budget(self, label: str, budget_ms: float) -> bool:
        s = self.stats(label)
        return s["p95"] <= budget_ms

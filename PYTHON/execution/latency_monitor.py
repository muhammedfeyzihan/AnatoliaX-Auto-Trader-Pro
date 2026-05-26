"""
latency_monitor.py — Round-trip latency, jitter, percentile tracking
"""
import time
import statistics
from collections import deque
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class LatencySample:
    operation: str
    rtt_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LatencyMonitor:
    """
    Her emir/veri/adaptor icin RTT olcer.
    P50, P95, P99, jitter ve alarm uretir.
    """

    def __init__(self, window_size: int = 1000, alert_p95_ms: float = 300.0):
        self.window_size = window_size
        self.alert_p95_ms = alert_p95_ms
        self._samples: Dict[str, deque] = {}
        self._alerts: List[str] = []

    def record(self, operation: str, start: float, end: float = None):
        if end is None:
            end = time.time()
        rtt = (end - start) * 1000
        if operation not in self._samples:
            self._samples[operation] = deque(maxlen=self.window_size)
        self._samples[operation].append(LatencySample(operation, rtt))
        if rtt > self.alert_p95_ms:
            self._alerts.append(f"LATENCY_ALERT: {operation} {rtt:.1f}ms > {self.alert_p95_ms}ms")

    def get_stats(self, operation: str) -> dict:
        samples = self._samples.get(operation, deque())
        if not samples:
            return {"operation": operation, "count": 0, "p50": 0, "p95": 0, "p99": 0, "jitter": 0}
        rtts = [s.rtt_ms for s in samples]
        rtts.sort()
        n = len(rtts)
        if n % 2 == 0:
            p50 = (rtts[n // 2 - 1] + rtts[n // 2]) / 2
        else:
            p50 = rtts[n // 2]
        p95 = rtts[int(n * 0.95)] if n >= 20 else rtts[-1]
        p99 = rtts[int(n * 0.99)] if n >= 100 else rtts[-1]
        jitter = statistics.stdev(rtts) if n >= 2 else 0.0
        return {
            "operation": operation,
            "count": n,
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "jitter": round(jitter, 2),
        }

    def get_all_stats(self) -> dict:
        return {op: self.get_stats(op) for op in self._samples}

    def get_alerts(self) -> List[str]:
        return self._alerts.copy()

    def clear_alerts(self):
        self._alerts.clear()

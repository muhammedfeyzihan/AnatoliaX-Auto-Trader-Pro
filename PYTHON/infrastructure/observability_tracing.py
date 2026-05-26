"""
infrastructure/observability_tracing.py — Distributed Observability & Tracing (Phase 2)
Module 21 from anatoliax_prompt_v6.txt

Features:
  - OpenTelemetry trace context: trace_id, span_id, parent_span_id
  - Trace path: Tick -> Signal -> Risk -> Execution -> Fill
  - Latency histograms: P50, P95, P99 per stage
  - Prometheus metrics: throughput, error_rate, queue_depth, memory_usage
"""

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict, deque


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    start_ns: int
    end_ns: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)


class DistributedObservability:
    """
    OpenTelemetry-compatible distributed tracing + Prometheus-style metrics.
    """

    def __init__(self):
        self._spans: List[Span] = []
        self._latency_buckets: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._throughput_counters: Dict[str, int] = defaultdict(int)
        self._error_counters: Dict[str, int] = defaultdict(int)
        self._queue_depths: Dict[str, int] = {}

    def start_span(self, trace_id: str, span_id: str, parent_span_id: Optional[str], operation: str) -> Span:
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_ns=time.time_ns(),
        )
        self._spans.append(span)
        return span

    def end_span(self, span: Span):
        span.end_ns = time.time_ns()
        latency_ms = (span.end_ns - span.start_ns) / 1e6
        self._latency_buckets[span.operation].append(latency_ms)

    def record_throughput(self, operation: str, count: int = 1):
        self._throughput_counters[operation] += count

    def record_error(self, operation: str, count: int = 1):
        self._error_counters[operation] += count

    def record_queue_depth(self, queue_name: str, depth: int):
        self._queue_depths[queue_name] = depth

    def latency_percentiles(self, operation: str) -> Dict[str, float]:
        vals = list(self._latency_buckets.get(operation, []))
        if not vals:
            return {}
        vals.sort()
        n = len(vals)
        return {
            "p50": vals[n // 2] if n >= 2 else vals[0],
            "p95": vals[int(n * 0.95)] if n >= 2 else vals[0],
            "p99": vals[int(n * 0.99)] if n >= 2 else vals[0],
            "mean": statistics.mean(vals),
        }

    def get_metrics(self) -> Dict:
        return {
            "throughput": dict(self._throughput_counters),
            "errors": dict(self._error_counters),
            "queue_depths": dict(self._queue_depths),
            "latencies": {op: self.latency_percentiles(op) for op in self._latency_buckets},
        }

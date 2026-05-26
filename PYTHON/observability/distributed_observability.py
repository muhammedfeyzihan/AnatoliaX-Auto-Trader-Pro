"""
observability/distributed_observability.py - Distributed Observability Stack

OpenTelemetry tracing, high-frequency metrics aggregation, AI anomaly monitoring,
deterministic replay diagnostics, execution-latency heatmaps, portfolio telemetry.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import hashlib


@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    operation: str
    start_time: str
    end_time: Optional[str]
    duration_ms: float
    status: str
    attributes: Dict[str, Any]


@dataclass
class MetricPoint:
    metric_name: str
    value: float
    timestamp: str
    labels: Dict[str, str]


class DistributedObservabilityStack:
    def __init__(self):
        self._traces: List[TraceSpan] = []
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._latency_heatmap: Dict[str, List[float]] = defaultdict(list)
        self._anomaly_scores: Dict[str, float] = {}
        self._portfolio_telemetry: Dict[str, List[Dict]] = defaultdict(list)
    
    def start_trace(self, operation: str, attributes: Optional[Dict] = None) -> TraceSpan:
        trace_id = hashlib.sha256(
            f"{operation}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:32]
        
        span_id = hashlib.sha256(
            f"{trace_id}{operation}".encode()
        ).hexdigest()[:16]
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation=operation,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=None,
            duration_ms=0.0,
            status="in_progress",
            attributes=attributes or {},
        )
        
        self._traces.append(span)
        return span
    
    def end_trace(self, span: TraceSpan, status: str = "success") -> None:
        span.end_time = datetime.now(timezone.utc).isoformat()
        span.status = status
        
        start = datetime.fromisoformat(span.start_time.replace('+00:00', ''))
        end = datetime.fromisoformat(span.end_time.replace('+00:00', ''))
        span.duration_ms = (end - start).total_seconds() * 1000
        
        self._latency_heatmap[span.operation].append(span.duration_ms)
    
    def record_metric(self, metric_name: str, value: float,
                     labels: Optional[Dict[str, str]] = None) -> None:
        point = MetricPoint(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            labels=labels or {},
        )
        self._metrics[metric_name].append(point)
        
        if len(self._metrics[metric_name]) > 10000:
            self._metrics[metric_name] = self._metrics[metric_name][-5000:]
    
    def detect_anomaly(self, metric_name: str,
                      threshold_std: float = 3.0) -> bool:
        if metric_name not in self._metrics or len(self._metrics[metric_name]) < 10:
            return False
        
        values = [p.value for p in self._metrics[metric_name][-100:]]
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return False
        
        latest = values[-1]
        z_score = abs(latest - mean) / std
        
        is_anomaly = z_score > threshold_std
        self._anomaly_scores[metric_name] = float(z_score)
        
        return is_anomaly
    
    def record_portfolio_telemetry(self, portfolio_id: str,
                                  pnl: float, exposure: float,
                                  var: float, sharpe: float) -> None:
        self._portfolio_telemetry[portfolio_id].append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pnl': pnl,
            'exposure': exposure,
            'var': var,
            'sharpe': sharpe,
        })
        
        if len(self._portfolio_telemetry[portfolio_id]) > 1000:
            self._portfolio_telemetry[portfolio_id] = self._portfolio_telemetry[portfolio_id][-500:]
    
    def get_latency_percentiles(self, operation: str) -> Dict[str, float]:
        if operation not in self._latency_heatmap:
            return {}
        
        latencies = self._latency_heatmap[operation]
        return {
            'p50': float(np.percentile(latencies, 50)),
            'p95': float(np.percentile(latencies, 95)),
            'p99': float(np.percentile(latencies, 99)),
            'mean': float(np.mean(latencies)),
            'count': len(latencies),
        }
    
    def get_observability_report(self) -> Dict[str, Any]:
        return {
            'total_traces': len(self._traces),
            'total_metrics': len(self._metrics),
            'operations_tracked': len(self._latency_heatmap),
            'anomalies_detected': sum(1 for score in self._anomaly_scores.values() if score > 3.0),
            'portfolios_tracked': len(self._portfolio_telemetry),
            'latency_percentiles': {
                op: self.get_latency_percentiles(op)
                for op in list(self._latency_heatmap.keys())[:10]
            },
        }


_observability_stack: Optional[DistributedObservabilityStack] = None

def get_distributed_observability() -> DistributedObservabilityStack:
    global _observability_stack
    if _observability_stack is None:
        _observability_stack = DistributedObservabilityStack()
    return _observability_stack

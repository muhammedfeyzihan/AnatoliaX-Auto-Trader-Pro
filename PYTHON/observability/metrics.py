"""
metrics.py — Prometheus-compatible metrics pipeline
Gauge, Counter, Histogram kollektorleri.
"""
import time
from collections import defaultdict
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class MetricSample:
    name: str
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """
    Basit metrics kollektoru. Prometheus pushgateway'e veya dosyaya yazilabilir.
    """

    def __init__(self):
        self._gauges: Dict[str, List[MetricSample]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def gauge(self, name: str, value: float, labels: dict = None):
        self._gauges[name].append(MetricSample(name, value, labels or {}))

    def counter(self, name: str, value: float = 1.0, labels: dict = None):
        self._counters[name] += value

    def histogram(self, name: str, value: float, labels: dict = None):
        self._histograms[name].append(value)

    def get_prometheus_format(self) -> str:
        lines = []
        for name, samples in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            for s in samples[-10:]:
                label_str = ",".join(f'{k}="{v}"' for k, v in s.labels.items())
                lines.append(f'{name}{{{label_str}}} {s.value}')
        for name, total in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f'{name} {total}')
        for name, values in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f'{name}_count {len(values)}')
            lines.append(f'{name}_sum {sum(values):.4f}')
            if values:
                vals = sorted(values)
                for p in [0.50, 0.95, 0.99]:
                    idx = int(len(vals) * p)
                    lines.append(f'{name}_bucket{{le="{p}"}} {vals[idx]:.4f}')
        return "\n".join(lines)

    def get_summary(self) -> dict:
        return {
            "gauges": {k: len(v) for k, v in self._gauges.items()},
            "counters": dict(self._counters),
            "histograms": {k: {"count": len(v), "sum": round(sum(v), 2)} for k, v in self._histograms.items()},
        }

"""
latency_precision.py — Millisecond-precision latency export.
K231: LatencyPrecisionExport (minor enhancement to LatencyMonitor).
"""
import json
import csv
from typing import Dict, List
from datetime import datetime, timezone
from execution.latency_monitor import LatencyMonitor


class LatencyPrecisionExport:
    """
    LatencyMonitor'dan alinan istatistikleri
    millisecond precision ile JSON/CSV'ye export eder.
    """

    def __init__(self, monitor: LatencyMonitor):
        self.monitor = monitor

    def export_json(self, path: str):
        stats = self.monitor.get_all_stats()
        enriched = {}
        for op, s in stats.items():
            enriched[op] = {
                **s,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "precision": "ms",
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2)

    def export_csv(self, path: str):
        stats = self.monitor.get_all_stats()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["operation", "count", "p50", "p95", "p99", "jitter"])
            writer.writeheader()
            for op, s in stats.items():
                writer.writerow(s)

    def to_prometheus(self) -> List[str]:
        lines = []
        stats = self.monitor.get_all_stats()
        for op, s in stats.items():
            safe_op = op.replace(" ", "_").replace("-", "_")
            lines.append(f'# TYPE latency_ms_{safe_op} histogram')
            lines.append(f'latency_ms_{safe_op}_p50 {s["p50"]}')
            lines.append(f'latency_ms_{safe_op}_p95 {s["p95"]}')
            lines.append(f'latency_ms_{safe_op}_p99 {s["p99"]}')
        return lines

"""
dashboard.py — Real-time observability dashboard + Grafana JSON export.
K228: ObservabilityDashboard.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


@dataclass
class Panel:
    title: str = ""
    metric: str = ""
    chart_type: str = "timeseries"
    targets: List[Dict] = field(default_factory=list)


class ObservabilityDashboard:
    """
    Grafana-compatible dashboard JSON uretici.
    Prometheus metriklerini Grafana panel'lerine donusturur.
    """

    def __init__(self, title: str = "AnatoliaX Dashboard", uid: str = "anatoliax-v1"):
        self.title = title
        self.uid = uid
        self._panels: List[Panel] = []
        self._alerts: List[Dict] = []

    def add_panel(self, panel: Panel):
        self._panels.append(panel)

    def add_alert(self, name: str, expr: str, threshold: float, severity: str = "warning"):
        self._alerts.append({
            "name": name,
            "expr": expr,
            "threshold": threshold,
            "severity": severity,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def to_grafana_json(self) -> Dict:
        panels_json = []
        for i, p in enumerate(self._panels):
            panels_json.append({
                "id": i + 1,
                "title": p.title,
                "type": p.chart_type,
                "targets": [{"expr": t["expr"], "legendFormat": t.get("legend", "")} for t in p.targets],
                "gridPos": {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8},
            })
        return {
            "dashboard": {
                "title": self.title,
                "uid": self.uid,
                "panels": panels_json,
                "tags": ["anatoliax", "trading"],
                "timezone": "Europe/Istanbul",
            },
            "overwrite": True,
        }

    def export_grafana(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_grafana_json(), f, indent=2, ensure_ascii=False)

    def add_default_panels(self):
        self.add_panel(Panel(
            title="P50/P95/P99 Latency",
            metric="latency_seconds",
            chart_type="timeseries",
            targets=[
                {"expr": "histogram_quantile(0.50, rate(latency_seconds_bucket[5m]))", "legend": "P50"},
                {"expr": "histogram_quantile(0.95, rate(latency_seconds_bucket[5m]))", "legend": "P95"},
                {"expr": "histogram_quantile(0.99, rate(latency_seconds_bucket[5m]))", "legend": "P99"},
            ],
        ))
        self.add_panel(Panel(
            title="Daily PnL",
            metric="daily_pnl",
            chart_type="graph",
            targets=[{"expr": "daily_pnl", "legend": "PnL"}],
        ))
        self.add_panel(Panel(
            title="Active Positions",
            metric="active_positions",
            chart_type="stat",
            targets=[{"expr": "active_positions", "legend": "Positions"}],
        ))
        self.add_panel(Panel(
            title="Kill Switch Status",
            metric="kill_switch_status",
            chart_type="stat",
            targets=[{"expr": "kill_switch_status", "legend": "Status"}],
        ))
        self.add_panel(Panel(
            title="Win Rate",
            metric="win_rate",
            chart_type="gauge",
            targets=[{"expr": "win_rate", "legend": "Win Rate"}],
        ))

    def get_status(self) -> Dict:
        return {
            "title": self.title,
            "uid": self.uid,
            "panels": len(self._panels),
            "alerts": len(self._alerts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

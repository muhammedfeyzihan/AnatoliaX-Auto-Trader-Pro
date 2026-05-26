"""
test_dashboard.py — Tests for ObservabilityDashboard (K228)
"""
import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from observability.dashboard import ObservabilityDashboard, Panel


class TestObservabilityDashboard:
    def test_add_panel(self):
        dash = ObservabilityDashboard()
        dash.add_panel(Panel(title="Test", metric="test_metric", chart_type="graph", targets=[{"expr": "up"}]))
        assert len(dash._panels) == 1

    def test_add_alert(self):
        dash = ObservabilityDashboard()
        dash.add_alert("HighLatency", "latency > 500", 500, "critical")
        assert len(dash._alerts) == 1

    def test_to_grafana_json(self):
        dash = ObservabilityDashboard(title="TestDash", uid="test-1")
        dash.add_panel(Panel(title="Panel1", metric="m1", chart_type="timeseries", targets=[{"expr": "a", "legend": "A"}]))
        g = dash.to_grafana_json()
        assert g["dashboard"]["title"] == "TestDash"
        assert g["dashboard"]["uid"] == "test-1"
        assert len(g["dashboard"]["panels"]) == 1

    def test_export_grafana(self):
        dash = ObservabilityDashboard()
        dash.add_default_panels()
        path = "test_dashboard.json"
        dash.export_grafana(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "dashboard" in data
        assert len(data["dashboard"]["panels"]) >= 5

    def test_default_panels(self):
        dash = ObservabilityDashboard()
        dash.add_default_panels()
        assert len(dash._panels) >= 5
        titles = [p.title for p in dash._panels]
        assert "P50/P95/P99 Latency" in titles
        assert "Daily PnL" in titles

    def test_get_status(self):
        dash = ObservabilityDashboard()
        dash.add_panel(Panel(title="P", metric="m"))
        status = dash.get_status()
        assert status["panels"] == 1
        assert status["alerts"] == 0

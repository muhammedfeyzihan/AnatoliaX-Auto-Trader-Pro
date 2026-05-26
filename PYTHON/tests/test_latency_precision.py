"""
test_latency_precision.py — Tests for LatencyPrecisionExport (K231)
"""
import pytest
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.latency_monitor import LatencyMonitor
from execution.latency_precision import LatencyPrecisionExport


class TestLatencyPrecisionExport:
    def test_export_json(self):
        mon = LatencyMonitor(window_size=100)
        mon.record("place_order", start=0.0, end=0.1)
        mon.record("place_order", start=0.0, end=0.2)
        exp = LatencyPrecisionExport(mon)
        path = "test_latency.json"
        exp.export_json(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "place_order" in data
        assert data["place_order"]["precision"] == "ms"
        os.remove(path)

    def test_export_csv(self):
        mon = LatencyMonitor(window_size=100)
        mon.record("place_order", start=0.0, end=0.1)
        exp = LatencyPrecisionExport(mon)
        path = "test_latency.csv"
        exp.export_csv(path)
        assert os.path.exists(path)
        os.remove(path)

    def test_to_prometheus(self):
        mon = LatencyMonitor(window_size=100)
        mon.record("place_order", start=0.0, end=0.1)
        exp = LatencyPrecisionExport(mon)
        lines = exp.to_prometheus()
        assert any("latency_ms_place_order_p50" in line for line in lines)

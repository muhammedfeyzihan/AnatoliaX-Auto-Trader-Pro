"""
Test: PYTHON.hft.latency_tracker
RTT measurement and statistics.
"""
import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.latency_tracker import LatencyTracker


class TestLatencyTracker:
    def test_record_and_stats(self):
        lt = LatencyTracker()
        lt.record("order", 100.0)
        lt.record("order", 200.0)
        lt.record("order", 300.0)
        stats = lt.stats("order")
        assert stats["count"] == 3
        assert stats["mean"] == 200.0
        assert stats["p50"] == 200.0

    def test_timer(self):
        lt = LatencyTracker()
        lt.start_timer("test")
        time.sleep(0.01)
        latency = lt.stop_timer("test")
        assert latency >= 5.0  # at least 5ms

    def test_within_budget(self):
        lt = LatencyTracker()
        lt.record("order", 100.0)
        assert lt.is_within_budget("order", 500.0) is True
        assert lt.is_within_budget("order", 50.0) is False

    def test_all_stats(self):
        lt = LatencyTracker()
        lt.record("a", 10.0)
        lt.record("b", 20.0)
        all_s = lt.all_stats()
        assert "a" in all_s
        assert "b" in all_s

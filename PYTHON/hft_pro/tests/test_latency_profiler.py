"""
tests/test_latency_profiler.py — LatencyProfiler birim testleri
"""
import pytest
from hft_pro.latency.profiler import LatencyProfiler, LatencyStage


class TestLatencyProfiler:
    def test_record_and_report(self):
        lp = LatencyProfiler()
        import time
        t = time.time_ns()
        lp.record(LatencyStage.FEED_ARRIVAL, t)
        lp.record(LatencyStage.FEED_ARRIVAL, t + 1_000_000)
        report = lp.get_report()
        assert LatencyStage.FEED_ARRIVAL.name in report.stages

    def test_alert_if_p99_exceeds(self):
        lp = LatencyProfiler()
        t = 1_000_000_000
        for i in range(200):
            lp.record(LatencyStage.SIGNAL_COMPUTE, t + i * 1_000_000)
        assert lp.alert_if_p99_exceeds(500_000) is True

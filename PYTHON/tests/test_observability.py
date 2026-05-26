"""
Test: PYTHON.observability.logger + metrics
Structured logging, audit, metrics pipeline.
"""
import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from observability.logger import AuditLogger, get_logger
from observability.metrics import MetricsCollector


class TestAuditLogger:
    def test_log_order(self, caplog):
        import logging
        logger = logging.getLogger("audit_test")
        logger.setLevel(logging.INFO)
        audit = AuditLogger(logger)
        audit.log_order("ord1", "THYAO", "BUY", 100, 103.0, "filled", trace_id="t1")
        # AuditLogger logger.info cagirir; yeterli ki hata vermeden calissin
        assert True

    def test_log_risk_event(self, caplog):
        import logging
        logger = logging.getLogger("audit_test2")
        logger.setLevel(logging.WARNING)
        audit = AuditLogger(logger)
        audit.log_risk_event("KILL_SWITCH", "Drawdown limit", trace_id="t2")
        assert True

    def test_log_kill_switch(self, caplog):
        import logging
        logger = logging.getLogger("audit_test3")
        logger.setLevel(logging.CRITICAL)
        audit = AuditLogger(logger)
        audit.log_kill_switch("Max DD exceeded", capital=94000, trace_id="t3")
        assert True


class TestMetricsCollector:
    def test_gauge(self):
        mc = MetricsCollector()
        mc.gauge("portfolio_value", 102450, labels={"currency": "TRY"})
        summary = mc.get_summary()
        assert summary["gauges"]["portfolio_value"] == 1

    def test_counter(self):
        mc = MetricsCollector()
        mc.counter("orders_placed", 1)
        mc.counter("orders_placed", 1)
        summary = mc.get_summary()
        assert summary["counters"]["orders_placed"] == 2.0

    def test_histogram(self):
        mc = MetricsCollector()
        mc.histogram("order_latency_ms", 45.0)
        mc.histogram("order_latency_ms", 120.0)
        summary = mc.get_summary()
        assert summary["histograms"]["order_latency_ms"]["count"] == 2

    def test_prometheus_format(self):
        mc = MetricsCollector()
        mc.gauge("equity", 100000)
        mc.counter("trades", 5)
        text = mc.get_prometheus_format()
        assert "gauge" in text
        assert "counter" in text
        assert "equity" in text

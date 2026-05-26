"""
Test: PYTHON.execution.engine + order_manager + latency_monitor
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.engine import UnifiedExecutionEngine, OrderSide, OrderStatus
from execution.order_manager import OrderManager
from execution.latency_monitor import LatencyMonitor


class TestUnifiedExecutionEngine:
    def test_backtest_order_filled(self):
        engine = UnifiedExecutionEngine(mode="backtest")
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 100
        assert order.source == "backtest"

    def test_live_order_with_mock_broker(self):
        def mock_broker(order):
            return {"filled": True, "filled_size": order.size, "avg_price": order.price}

        engine = UnifiedExecutionEngine(mode="live", broker_adapter=mock_broker)
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        assert order.status == OrderStatus.FILLED

    def test_live_order_retry(self):
        calls = []

        def failing_broker(order):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("fail")
            return {"filled": True, "filled_size": order.size, "avg_price": order.price}

        engine = UnifiedExecutionEngine(mode="live", broker_adapter=failing_broker, max_latency_ms=1000)
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        assert order.status == OrderStatus.FILLED
        assert order.retries >= 2

    def test_cancel_order(self):
        def mock_broker(order):
            return {"filled": False}  # Live modda hemen doldurma
        engine = UnifiedExecutionEngine(mode="live", broker_adapter=mock_broker)
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        assert engine.cancel_order(order.id) is True
        assert order.status == OrderStatus.CANCELLED

    def test_reconcile(self):
        engine = UnifiedExecutionEngine(mode="live")
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        engine.reconcile([{"id": order.id, "status": "filled", "filled_size": 100, "avg_price": 103.0}])
        assert order.status == OrderStatus.FILLED


class TestOrderManager:
    def test_submit_and_retry(self):
        calls = []

        def submit_fn(payload):
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("fail")
            return {"status": "filled"}

        mgr = OrderManager(submit_fn=submit_fn, max_retries=3, base_delay=0.01)
        result = mgr.submit("ord1", {"size": 100})
        assert result["status"] == "filled"
        assert mgr._orders["ord1"]["retries"] == 1

    def test_reconcile(self):
        def submit_fn(payload):
            return {"status": "partial", "filled_size": 50}

        def status_fn(oid):
            return {"filled_size": 100}

        mgr = OrderManager(submit_fn=submit_fn, status_fn=status_fn)
        mgr.submit("ord1", {"size": 100})
        rec = mgr.reconcile("ord1")
        assert rec["status"] == "reconciled"

    def test_partial_fill_timeout(self):
        import time
        def submit_fn(payload):
            return {"status": "partial", "filled_size": 50, "partial": True}

        mgr = OrderManager(submit_fn=submit_fn, partial_fill_timeout_sec=0.01)
        mgr.submit("ord1", {"size": 100})
        time.sleep(0.02)
        expired = mgr.check_partial_fills()
        assert "ord1" in expired


class TestLatencyMonitor:
    def test_record_and_stats(self):
        mon = LatencyMonitor(window_size=100, alert_p95_ms=500)
        mon.record("place_order", start=0.0, end=0.1)
        mon.record("place_order", start=0.0, end=0.2)
        stats = mon.get_stats("place_order")
        assert stats["count"] == 2
        assert stats["p50"] == 150.0

    def test_alert(self):
        mon = LatencyMonitor(alert_p95_ms=10)
        mon.record("place_order", start=0.0, end=0.5)
        assert len(mon.get_alerts()) >= 1

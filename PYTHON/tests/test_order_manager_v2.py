"""
test_order_manager_v2.py — Tests for OrderManagerV2 (K221-K223)
"""
import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.order_manager_v2 import OrderManagerV2, OrderStatusV2


class TestOrderManagerV2:
    def test_submit_success(self):
        def submit_fn(payload):
            return {"status": "filled", "price": payload.get("price", 100)}

        mgr = OrderManagerV2(submit_fn=submit_fn)
        result = mgr.submit("ord1", {"symbol": "THYAO", "size": 100, "price": 150})
        assert result["status"] == "filled"
        assert mgr.get_order("ord1")["status"] == "filled"

    def test_submit_retry(self):
        calls = []

        def submit_fn(payload):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("fail")
            return {"status": "filled"}

        mgr = OrderManagerV2(submit_fn=submit_fn, base_delay=0.01)
        result = mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        assert result["status"] == "filled"
        assert mgr.get_order("ord1")["retries"] == 2

    def test_submit_error(self):
        def submit_fn(payload):
            raise RuntimeError("fail")

        mgr = OrderManagerV2(submit_fn=submit_fn, max_retries=1, base_delay=0.01)
        with pytest.raises(RuntimeError):
            mgr.submit("ord1", {"symbol": "THYAO", "size": 100})

    def test_slippage_alert(self):
        def submit_fn(payload):
            return {"status": "filled", "price": 110}

        mgr = OrderManagerV2(submit_fn=submit_fn, slippage_tolerance_pct=0.01)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100, "price": 100})
        order = mgr.get_order("ord1")
        assert "slippage_alert" in order

    def test_reconcile(self):
        def submit_fn(payload):
            return {"status": "filled", "filled_size": 50}

        def status_fn(oid):
            return {"status": "filled", "filled_size": 100}

        mgr = OrderManagerV2(submit_fn=submit_fn, status_fn=status_fn)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        rec = mgr.reconcile("ord1")
        assert rec["status"] == "filled"

    def test_check_stale_orders(self):
        def submit_fn(payload):
            return {"status": "submitted"}

        def cancel_fn(oid):
            return True

        mgr = OrderManagerV2(submit_fn=submit_fn, cancel_fn=cancel_fn, stale_threshold_sec=0)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        time.sleep(0.05)
        stale = mgr.check_stale_orders()
        assert "ord1" in stale
        assert mgr.get_order("ord1")["status"] == OrderStatusV2.STALE.value

    def test_check_partial_fills_timeout(self):
        def submit_fn(payload):
            return {"status": "partial", "partial": True}

        mgr = OrderManagerV2(submit_fn=submit_fn, partial_fill_timeout_sec=0.01)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        time.sleep(0.02)
        expired = mgr.check_partial_fills()
        assert "ord1" in expired

    def test_cancel(self):
        def cancel_fn(oid):
            return True

        def submit_fn(payload):
            return {"status": "submitted"}

        mgr = OrderManagerV2(submit_fn=submit_fn, cancel_fn=cancel_fn)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        assert mgr.cancel("ord1") is True
        assert mgr.get_order("ord1")["status"] == OrderStatusV2.CANCELLED.value

    def test_summary(self):
        def submit_fn(payload):
            return {"status": "filled"}

        mgr = OrderManagerV2(submit_fn=submit_fn)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        summary = mgr.get_summary()
        assert summary["total_orders"] == 1
        assert summary["filled"] == 1

    def test_event_callback(self):
        events = []

        def on_event(event_type, oid, data):
            events.append(event_type)

        def submit_fn(payload):
            return {"status": "filled"}

        mgr = OrderManagerV2(submit_fn=submit_fn, on_event=on_event)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        assert "SUBMITTED" in events

    def test_reset(self):
        def submit_fn(payload):
            return {"status": "filled"}

        mgr = OrderManagerV2(submit_fn=submit_fn)
        mgr.submit("ord1", {"symbol": "THYAO", "size": 100})
        mgr.reset()
        assert mgr.get_summary()["total_orders"] == 0

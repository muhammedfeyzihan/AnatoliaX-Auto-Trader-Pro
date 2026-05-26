"""
Test: PYTHON.execution.order_manager
OrderManager retry, partial fill, reconciliation.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.order_manager import OrderManager


class TestOrderManager:
    def test_submit_success(self):
        submit_fn = MagicMock(return_value={"status": "filled", "filled_size": 100})
        om = OrderManager(submit_fn=submit_fn, max_retries=2)
        result = om.submit("ord1", {"symbol": "THYAO", "side": "BUY", "size": 100})
        assert result["status"] == "filled"
        assert om._orders["ord1"]["status"] == "filled"

    def test_submit_retry_then_success(self):
        submit_fn = MagicMock(side_effect=[Exception("timeout"), {"status": "filled"}])
        om = OrderManager(submit_fn=submit_fn, max_retries=2, base_delay=0.01)
        result = om.submit("ord2", {"symbol": "THYAO", "side": "BUY", "size": 100})
        assert result["status"] == "filled"
        assert submit_fn.call_count == 2

    def test_submit_all_retries_fail(self):
        submit_fn = MagicMock(side_effect=Exception("timeout"))
        om = OrderManager(submit_fn=submit_fn, max_retries=2, base_delay=0.01)
        with pytest.raises(Exception):
            om.submit("ord3", {"symbol": "THYAO", "side": "BUY", "size": 100})
        assert om._orders["ord3"]["status"] == "error"

    def test_partial_fill_tracking(self):
        submit_fn = MagicMock(return_value={"status": "partial", "partial": True, "filled_size": 50})
        om = OrderManager(submit_fn=submit_fn, max_retries=0)
        om.submit("ord4", {"symbol": "THYAO", "side": "BUY", "size": 100})
        assert "ord4" in om._pending_partials
        assert om._orders["ord4"]["status"] == "partial"

    def test_reconcile(self):
        submit_fn = MagicMock(return_value={"status": "filled", "filled_size": 100})
        status_fn = MagicMock(return_value={"filled_size": 150})
        om = OrderManager(submit_fn=submit_fn, status_fn=status_fn, max_retries=0)
        om.submit("ord5", {"symbol": "THYAO", "side": "BUY", "size": 100})
        result = om.reconcile("ord5")
        assert result["status"] == "reconciled"

    def test_reconcile_without_status_fn(self):
        submit_fn = MagicMock(return_value={"status": "filled"})
        om = OrderManager(submit_fn=submit_fn, max_retries=0)
        om.submit("ord6", {"symbol": "THYAO", "side": "BUY", "size": 100})
        result = om.reconcile("ord6")
        assert result["status"] == "filled"

    def test_check_partial_fills(self):
        from datetime import datetime, timedelta
        submit_fn = MagicMock(return_value={"status": "partial", "partial": True})
        om = OrderManager(submit_fn=submit_fn, max_retries=0, partial_fill_timeout_sec=0.01)
        om.submit("ord7", {"symbol": "THYAO", "side": "BUY", "size": 100})
        import time
        time.sleep(0.05)
        expired = om.check_partial_fills()
        assert "ord7" in expired
        assert om._orders["ord7"]["status"] == "partial_expired"

    def test_get_summary(self):
        submit_fn = MagicMock(return_value={"status": "filled"})
        om = OrderManager(submit_fn=submit_fn, max_retries=0)
        om.submit("a", {"symbol": "THYAO"})
        om.submit("b", {"symbol": "GARAN"})
        summary = om.get_summary()
        assert summary["total_orders"] == 2
        assert summary["filled"] == 2
        assert summary["errors"] == 0

    def test_get_summary_with_errors(self):
        submit_fn = MagicMock(side_effect=Exception("fail"))
        om = OrderManager(submit_fn=submit_fn, max_retries=0)
        try:
            om.submit("c", {"symbol": "THYAO"})
        except Exception:
            pass
        summary = om.get_summary()
        assert summary["errors"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

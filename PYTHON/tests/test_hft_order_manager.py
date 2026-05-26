"""
Test: PYTHON.hft.order_manager
Order lifecycle, fills, cancellations, queue position.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.order_manager import HFTOrderManager, HFTOrderStatus


class TestHFTOrderManager:
    def test_create_and_submit(self):
        om = HFTOrderManager()
        order = om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        assert order.status == HFTOrderStatus.PENDING
        assert om.submit("o1") is True
        assert order.status == HFTOrderStatus.SUBMITTED

    def test_fill_partial(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.fill("o1", 50, 100.0)
        order = om.get_order("o1")
        assert order.status == HFTOrderStatus.PARTIAL_FILL
        assert order.filled_size == 50

    def test_fill_full(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.fill("o1", 100, 100.0)
        order = om.get_order("o1")
        assert order.status == HFTOrderStatus.FILLED
        assert order.filled_size == 100

    def test_cancel(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        assert om.cancel("o1") is True
        assert om.get_order("o1").status == HFTOrderStatus.CANCELLED

    def test_cancel_filled_fails(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.fill("o1", 100, 100.0)
        assert om.cancel("o1") is False

    def test_cancel_stale(self):
        om = HFTOrderManager(max_pending_ttl_seconds=0.0)
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        import time
        time.sleep(0.01)
        cancelled = om.cancel_stale()
        assert "o1" in cancelled

    def test_get_open_orders(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.create_order("o2", "GARAN", "BUY", 50, 50.0)
        open_orders = om.get_open_orders("THYAO")
        assert len(open_orders) == 1
        assert open_orders[0].order_id == "o1"

    def test_avg_fill_price(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.fill("o1", 50, 100.0)
        om.fill("o1", 50, 110.0)
        order = om.get_order("o1")
        assert order.avg_fill_price == 105.0

    def test_stats(self):
        om = HFTOrderManager()
        om.create_order("o1", "THYAO", "BUY", 100, 100.0)
        om.submit("o1")
        om.fill("o1", 100, 100.0)
        stats = om.stats()
        assert stats["total_orders"] == 1
        assert stats["filled"] == 1

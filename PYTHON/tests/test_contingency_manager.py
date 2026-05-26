"""
Test: PYTHON.execution.contingency_manager
Bracket, OCO, TrailingStop, Iceberg emulation.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.contingency_manager import ContingencyManager
from execution.order_types import BracketOrder, OCOOrder, TrailingStopOrder, IcebergOrder


class TestContingencyManager:
    def test_bracket_submit(self):
        mgr = ContingencyManager()
        result = mgr.submit_bracket(BracketOrder(symbol="THYAO", side="BUY", size=100, entry_price=103.0, sl_price=99.0, tp_price=110.0))
        assert result["status"] == "PENDING"
        assert "entry_id" in result
        bracket = mgr.get_bracket(result["parent_id"])
        assert bracket["sl_price"] == 99.0

    def test_bracket_entry_fill_activates(self):
        mgr = ContingencyManager()
        result = mgr.submit_bracket(BracketOrder(symbol="THYAO", side="BUY", size=100, entry_price=103.0, sl_price=99.0, tp_price=110.0))
        entry_id = result["entry_id"]
        mgr.on_fill(entry_id, filled_size=100, avg_price=103.0)
        bracket = mgr.get_bracket(result["parent_id"])
        assert bracket["entry_filled"] is True
        assert bracket["status"] == "ACTIVE"

    def test_bracket_with_trailing(self):
        mgr = ContingencyManager()
        result = mgr.submit_bracket(BracketOrder(
            symbol="THYAO", side="BUY", size=100, entry_price=103.0,
            sl_price=99.0, tp_price=110.0, trailing_distance=2.0,
        ))
        mgr.on_fill(result["entry_id"], filled_size=100, avg_price=103.0)
        ts = mgr.get_trailing(result["sl_id"])
        assert ts is not None
        assert ts.distance == 2.0

    def test_oco_submit(self):
        mgr = ContingencyManager()
        result = mgr.submit_oco(OCOOrder(symbol="THYAO", side="SELL", size=100, limit_price=110.0, stop_price=99.0))
        assert result["status"] == "PENDING"
        oco = mgr.get_oco(result["parent_id"])
        assert oco["leg_a_id"] != oco["leg_b_id"]

    def test_oco_one_fills_other_cancelled(self):
        mgr = ContingencyManager()
        result = mgr.submit_oco(OCOOrder(symbol="THYAO", side="SELL", size=100, limit_price=110.0, stop_price=99.0))
        leg_a = result["leg_a_id"]
        leg_b = result["leg_b_id"]
        mgr.on_fill(leg_a, filled_size=100, avg_price=110.0)
        oco = mgr.get_oco(result["parent_id"])
        assert oco["status"] == "FILLED"
        assert oco["cancelled_id"] == leg_b

    def test_trailing_stop_update_and_trigger(self):
        mgr = ContingencyManager()
        ts = TrailingStopOrder(symbol="THYAO", side="SELL", size=100, distance=2.0, current_stop=98.0)
        result = mgr.submit_trailing_stop(ts)
        update = mgr.update_trailing(result["id"], current_price=104.0, is_long=True)
        assert update["triggered"] is False
        assert update["stop_price"] == 102.0
        trigger = mgr.update_trailing(result["id"], current_price=101.0, is_long=True)
        assert trigger["triggered"] is True

    def test_iceberg_submit(self):
        mgr = ContingencyManager()
        result = mgr.submit_iceberg(IcebergOrder(symbol="THYAO", side="BUY", total_size=1000, display_qty=100, price=103.0))
        assert result["status"] == "ACTIVE"
        assert len(result["slices"]) == 10

    def test_iceberg_fill_advances(self):
        mgr = ContingencyManager()
        result = mgr.submit_iceberg(IcebergOrder(symbol="THYAO", side="BUY", total_size=1000, display_qty=100, price=103.0))
        first_slice = result["slices"][0]
        mgr.on_fill(first_slice, filled_size=100, avg_price=103.0)
        iceberg = mgr.get_iceberg(result["parent_id"])
        assert iceberg["remaining"] == 900

    def test_get_methods(self):
        mgr = ContingencyManager()
        r = mgr.submit_bracket(BracketOrder(symbol="THYAO", side="BUY", size=100, entry_price=103.0, sl_price=99.0, tp_price=110.0))
        assert mgr.get_bracket(r["parent_id"]) is not None
        assert mgr.get_bracket("nonexistent") is None

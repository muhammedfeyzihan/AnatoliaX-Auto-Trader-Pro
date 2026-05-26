"""
Test: PYTHON.execution.order_types
Bracket, OCO, TrailingStop, Iceberg.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.order_types import (
    BracketOrder, OCOOrder, TrailingStopOrder, IcebergOrder,
    OrderType, TimeInForce,
)


class TestOrderTypes:
    def test_bracket_order_fields(self):
        b = BracketOrder(
            symbol="THYAO", side="BUY", size=100, entry_price=103.0,
            entry_type=OrderType.LIMIT, sl_price=99.0, tp_price=110.0,
        )
        assert b.entry_type == OrderType.LIMIT
        assert b.sl_price == 99.0
        assert b.tp_price == 110.0

    def test_oco_order(self):
        o = OCOOrder(symbol="THYAO", side="SELL", size=100, limit_price=110.0, stop_price=99.0)
        assert o.limit_price == 110.0
        assert o.stop_price == 99.0

    def test_trailing_stop_update_long(self):
        ts = TrailingStopOrder(symbol="THYAO", side="SELL", size=100, distance=2.0, current_stop=95.0)
        ts.update_stop(current_market_price=104.0, is_long=True)
        assert ts.current_stop == 102.0
        # Price drops, stop stays
        ts.update_stop(current_market_price=103.0, is_long=True)
        assert ts.current_stop == 102.0

    def test_trailing_stop_update_short(self):
        ts = TrailingStopOrder(symbol="THYAO", side="BUY", size=100, distance=2.0, current_stop=110.0)
        ts.update_stop(current_market_price=100.0, is_long=False)
        assert ts.current_stop == 102.0

    def test_trailing_stop_pct(self):
        ts = TrailingStopOrder(symbol="THYAO", side="SELL", size=100, distance_pct=2.0, current_stop=95.0)
        ts.update_stop(current_market_price=104.0, is_long=True)
        assert ts.current_stop == pytest.approx(101.92, abs=0.01)

    def test_iceberg_order(self):
        ice = IcebergOrder(symbol="THYAO", side="BUY", total_size=1000, display_qty=100, price=103.0)
        assert ice.total_size == 1000
        assert ice.display_qty == 100

    def test_time_in_force_enum(self):
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.IOC.value == "IOC"

    def test_order_type_enum(self):
        assert OrderType.MARKET.value == "market"
        assert OrderType.BRACKET.value == "bracket"
        assert OrderType.OCO.value == "oco"

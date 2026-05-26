"""
Test: PYTHON.risk.position
Position domain object: fills, P&L, side transitions.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.position import Position


class TestPosition:
    def test_default_flat(self):
        p = Position(symbol="THYAO")
        assert p.side == "FLAT"
        assert p.quantity == 0.0
        assert p.is_open is False

    def test_buy_opens_long(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 103.0, "BUY")
        assert p.side == "LONG"
        assert p.quantity == 100.0
        assert p.avg_entry_price == 103.0

    def test_multiple_buys_avg_price(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        p.apply_fill(100, 110.0, "BUY")
        assert p.quantity == 200.0
        assert p.avg_entry_price == 105.0

    def test_partial_sell_long(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        p.apply_fill(50, 110.0, "SELL", commission=10.0)
        assert p.quantity == 50.0
        assert p.realized_pnl == (110.0 - 100.0) * 50 - 10.0

    def test_full_sell_closes_long(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        p.apply_fill(100, 110.0, "SELL")
        assert p.side == "FLAT"
        assert p.quantity == 0.0
        assert p.realized_pnl == 1000.0

    def test_sell_opens_short(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 103.0, "SELL")
        assert p.side == "SHORT"
        assert p.quantity == 100.0

    def test_partial_buy_closes_short(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "SELL")
        p.apply_fill(50, 90.0, "BUY")
        assert p.quantity == 50.0
        assert p.realized_pnl == (100.0 - 90.0) * 50

    def test_full_buy_closes_short(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "SELL")
        p.apply_fill(100, 90.0, "BUY")
        assert p.side == "FLAT"
        assert p.realized_pnl == 1000.0

    def test_mark_price_long(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        p.mark_price(110.0)
        assert p.unrealized_pnl == 1000.0

    def test_mark_price_short(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "SELL")
        p.mark_price(90.0)
        assert p.unrealized_pnl == 1000.0

    def test_mark_price_flat(self):
        p = Position(symbol="THYAO")
        p.mark_price(110.0)
        assert p.unrealized_pnl == 0.0

    def test_zero_fill_noop(self):
        p = Position(symbol="THYAO")
        p.apply_fill(0, 100.0, "BUY")
        assert p.side == "FLAT"

    def test_to_dict(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        d = p.to_dict()
        assert d["symbol"] == "THYAO"
        assert d["quantity"] == 100.0
        assert "market_value" in d

    def test_commission_deducted_from_realized(self):
        p = Position(symbol="THYAO")
        p.apply_fill(100, 100.0, "BUY")
        p.apply_fill(100, 110.0, "SELL", commission=50.0)
        assert p.realized_pnl == 950.0

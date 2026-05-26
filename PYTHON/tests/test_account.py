"""
Test: PYTHON.risk.account
Account domain object: cash tracking, position limits, mark-to-market.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.account import Account


class TestAccount:
    def test_default_values(self):
        acc = Account()
        assert acc.cash == 100_000.0
        assert acc.equity == 100_000.0
        assert acc.open_position_count == 0

    def test_open_position_deducts_cash(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        ok = acc.open_position("THYAO", 100, 100.0)
        assert ok is True
        assert acc.cash == 90_000.0  # 100 * 100 = 10_000 deducted
        assert acc.open_position_count == 1

    def test_open_position_insufficient_cash(self):
        acc = Account(initial_cash=1000, max_position_value_pct=1.0)
        ok = acc.open_position("THYAO", 100, 100.0)
        assert ok is False
        assert acc.cash == 1000.0

    def test_close_position_credits_cash(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0)
        pnl = acc.close_position("THYAO", 100, 110.0)
        assert pnl == 1000.0
        assert acc.cash == 100_000 + 1000.0  # 90k + 11k proceeds
        assert acc.realized_pnl == 1000.0

    def test_close_position_partial(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0)
        pnl = acc.close_position("THYAO", 50, 110.0)
        assert pnl == 500.0
        # cash: 100k - 10k (buy) + 5.5k (sell 50@110)
        assert acc.cash == 95_500.0
        pos = acc.get_position("THYAO")
        assert pos.quantity == 50.0

    def test_mark_to_market(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0)
        acc.mark_to_market({"THYAO": 110.0})
        assert acc.unrealized_pnl == 1000.0
        assert acc.equity == 91_000.0  # cash 90k + unrealized 1k

    def test_max_position_limit(self):
        acc = Account(initial_cash=1_000_000, max_position_value_pct=0.01)
        ok, reason = acc.can_open_position("THYAO", 1000, 20.0)
        assert ok is False
        assert "exceeds" in reason.lower()

    def test_max_total_positions(self):
        acc = Account(initial_cash=1_000_000, max_total_positions=2)
        acc.open_position("THYAO", 10, 100.0)
        acc.open_position("GARAN", 10, 100.0)
        ok, reason = acc.can_open_position("ASELS", 10, 100.0)
        assert ok is False
        assert "max positions" in reason.lower()

    def test_total_return_pct(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0)
        acc.close_position("THYAO", 100, 110.0)
        assert acc.total_return_pct == pytest.approx(0.01, rel=1e-3)

    def test_to_dict(self):
        acc = Account(account_id="test", initial_cash=50_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0)
        d = acc.to_dict()
        assert d["account_id"] == "test"
        assert d["cash"] == 40_000.0
        assert "positions" in d
        assert "THYAO" in d["positions"]

    def test_commission_tracked(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        acc.open_position("THYAO", 100, 100.0, commission=50.0)
        assert acc.total_commission == 50.0

    def test_close_nonexistent_returns_none(self):
        acc = Account(initial_cash=100_000)
        pnl = acc.close_position("THYAO", 100, 110.0)
        assert pnl is None

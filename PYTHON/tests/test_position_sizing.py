"""
test_position_sizing.py — Advanced Position Sizing Tests
"""

import pytest
import math
from risk.position_sizing import PositionSizer


class TestPositionSizer:
    def test_kelly_basic(self):
        sizer = PositionSizer()
        f = sizer.kelly(win_rate=0.6, avg_win=100, avg_loss=50, fraction=0.25)
        # b = 2, f* = (2*0.6 - 0.4) / 2 = 0.4, *0.25 = 0.1
        assert f == pytest.approx(0.1, rel=1e-2)

    def test_kelly_negative_returns_zero(self):
        sizer = PositionSizer()
        f = sizer.kelly(win_rate=0.3, avg_win=50, avg_loss=100, fraction=0.25)
        assert f == 0.0

    def test_half_kelly(self):
        sizer = PositionSizer()
        f_half = sizer.half_kelly(win_rate=0.6, avg_win=100, avg_loss=50)
        f_full = sizer.kelly(win_rate=0.6, avg_win=100, avg_loss=50, fraction=0.5)
        assert f_half == f_full

    def test_optimal_f_basic(self):
        sizer = PositionSizer()
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        f = sizer.optimal_f(returns, steps=100)
        assert 0.0 <= f <= 1.0

    def test_optimal_f_empty(self):
        sizer = PositionSizer()
        assert sizer.optimal_f([]) == 0.0

    def test_optimal_f_no_losses(self):
        sizer = PositionSizer()
        assert sizer.optimal_f([0.01, 0.02, 0.03]) == 0.0

    def test_volatility_target(self):
        sizer = PositionSizer()
        size = sizer.volatility_target(base_size=100, realized_vol_20d=0.20, target_vol=0.10)
        assert size == 50.0

    def test_volatility_target_low_vol(self):
        sizer = PositionSizer()
        size = sizer.volatility_target(base_size=100, realized_vol_20d=0.05, target_vol=0.10)
        assert size == 200.0

    def test_size_fractional_kelly(self):
        sizer = PositionSizer(max_risk_per_trade_pct=0.02)
        qty = sizer.size(
            equity=100_000,
            price=100.0,
            method="fractional_kelly",
            win_rate=0.6,
            avg_win=100,
            avg_loss=50,
            fraction=0.25,
        )
        assert qty >= 1

    def test_size_fixed(self):
        sizer = PositionSizer(max_risk_per_trade_pct=0.02)
        qty = sizer.size(
            equity=100_000,
            price=100.0,
            method="fixed",
            risk_fraction=0.02,
        )
        assert qty == 20

    def test_size_max_risk_cap(self):
        sizer = PositionSizer(max_risk_per_trade_pct=0.02)
        qty = sizer.size(
            equity=100_000,
            price=100.0,
            method="fractional_kelly",
            win_rate=0.9,
            avg_win=1000,
            avg_loss=10,
            fraction=1.0,  # Would be huge without cap
        )
        # Should be capped at max_risk_per_trade_pct
        notional = qty * 100.0
        assert notional <= 100_000 * 0.02 + 1e-6

    def test_size_volatility_target(self):
        sizer = PositionSizer(max_risk_per_trade_pct=0.02)
        qty = sizer.size(
            equity=100_000,
            price=100.0,
            method="volatility_target",
            base_size=100,
            realized_vol_20d=0.20,
            target_vol=0.10,
        )
        assert qty >= 1

    def test_size_invalid_price(self):
        sizer = PositionSizer()
        qty = sizer.size(equity=100_000, price=0, method="fixed", risk_fraction=0.02)
        assert qty == 0

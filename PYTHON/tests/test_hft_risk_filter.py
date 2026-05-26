"""
Test: PYTHON.hft.risk_filter
Spread, slippage, rate-limit checks.
"""
import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.risk_filter import RiskFilter


class TestRiskFilter:
    def test_spread_filter_blocks_wide_spread(self):
        rf = RiskFilter(max_spread_pct=0.003)
        result = rf.check("THYAO", bid=100.0, ask=100.5, equity=100_000, open_position_count=0, proposed_size=10)
        assert result.allowed is False
        assert "Spread" in result.reason

    def test_position_count_limit(self):
        rf = RiskFilter(max_positions=2)
        result = rf.check("THYAO", bid=100.0, ask=100.01, equity=100_000, open_position_count=2, proposed_size=10)
        assert result.allowed is False
        assert "Max positions" in result.reason

    def test_rate_limit(self):
        rf = RiskFilter(max_trades_per_minute=2)
        rf.record_trade()
        rf.record_trade()
        result = rf.check("THYAO", bid=100.0, ask=100.01, equity=100_000, open_position_count=0, proposed_size=10)
        assert result.allowed is False
        assert "rate" in result.reason.lower()

    def test_size_adjustment(self):
        rf = RiskFilter(max_position_value_pct=0.01)
        result = rf.check("THYAO", bid=100.0, ask=100.0, equity=100_000, open_position_count=0, proposed_size=2000)
        # 2000 * 100 = 200k > 1% of 100k = 1k
        assert result.allowed is True
        assert result.adjusted_size < 2000

    def test_profit_feasibility(self):
        rf = RiskFilter(
            min_profit_target_pct=0.001,
            commission_rate=0.001,
            bsmv_rate=0.001,
            max_slippage_pct=0.002,
            max_position_value_pct=1.0,  # avoid size adjustment
        )
        result = rf.check("THYAO", bid=100.0, ask=100.0, equity=100_000, open_position_count=0, proposed_size=10)
        # total_cost = 0.004, min_profit = 0.001 <= 0.004
        assert result.allowed is False
        assert "profit" in result.reason.lower()

    def test_ok(self):
        rf = RiskFilter(max_spread_pct=0.01, max_position_value_pct=1.0, min_profit_target_pct=0.01)
        result = rf.check("THYAO", bid=100.0, ask=100.01, equity=100_000, open_position_count=0, proposed_size=10)
        assert result.allowed is True
        assert result.reason == "OK"

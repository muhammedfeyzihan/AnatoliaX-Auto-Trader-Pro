"""
test_bist_regulations.py — BIST Regulatory Compliance Tests
"""

import pytest
from datetime import datetime, timezone, timedelta
from risk.bist_regulations import (
    BISTRegulatoryChecker,
    VBTSMeasure,
    CircuitBreakerState,
)


class TestBISTRegulatoryChecker:
    def test_short_selling_always_banned(self):
        checker = BISTRegulatoryChecker()
        assert checker.is_short_selling_allowed("THYAO") is False
        assert checker.is_short_selling_allowed("GARAN") is False

    def test_price_limits_within_band(self):
        checker = BISTRegulatoryChecker()
        ref = 100.0
        result = checker.check_price_limits(110.0, ref)
        assert result["valid"] is True
        assert result["lower"] == 80.0
        assert result["upper"] == 120.0

    def test_price_limits_above_band(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_price_limits(125.0, 100.0)
        assert result["valid"] is False
        assert "outside" in result["reason"]

    def test_price_limits_below_band(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_price_limits(75.0, 100.0)
        assert result["valid"] is False

    def test_index_circuit_breaker_not_triggered(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_index_circuit_breaker(9600, 10000)
        assert state.triggered is False

    def test_index_circuit_breaker_minus_5(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_index_circuit_breaker(9500, 10000)
        # -5% trigger
        # Actually 9500 is -5%, let's check
        # 9500 is exactly -5% of 10000
        # The function checks change_pct <= level_pct
        # So -0.05 <= -0.05 -> True
        # Wait, let's compute: (9500-10000)/10000 = -0.05
        state = checker.check_index_circuit_breaker(9499, 10000)
        assert state.triggered is True
        assert state.level == -0.05
        assert state.duration_minutes == 15

    def test_index_circuit_breaker_minus_7(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_index_circuit_breaker(9299, 10000)
        assert state.triggered is True
        assert state.level == -0.07
        assert state.duration_minutes is None  # gün sonu

    def test_stock_circuit_breaker_low_tier(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_stock_circuit_breaker("THYAO", 5.5, 5.0)
        assert state.triggered is True
        assert state.level == 0.05

    def test_stock_circuit_breaker_mid_tier(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_stock_circuit_breaker("THYAO", 55.0, 50.0)
        assert state.triggered is True
        assert state.level == 0.075

    def test_stock_circuit_breaker_high_tier(self):
        checker = BISTRegulatoryChecker()
        state = checker.check_stock_circuit_breaker("THYAO", 110.0, 100.0)
        assert state.triggered is True
        assert state.level == 0.10

    def test_order_trade_ratio_pass(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_order_trade_ratio(30, 10)
        assert result["valid"] is True
        assert result["ratio"] == 3.0

    def test_order_trade_ratio_fail(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_order_trade_ratio(20, 10)
        assert result["valid"] is False
        assert result["ratio"] == 2.0

    def test_margin_requirement_pass(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_margin_requirement(100_000, 25_000)
        assert result["valid"] is True
        assert result["ratio"] == 0.25

    def test_margin_requirement_fail(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_margin_requirement(100_000, 15_000)
        assert result["valid"] is False
        assert result["ratio"] == 0.15

    def test_dividend_tax(self):
        checker = BISTRegulatoryChecker()
        result = checker.calculate_dividend_tax(1000.0)
        assert result["tax"] == 150.0
        assert result["net"] == 850.0
        assert result["rate"] == 0.15

    def test_vbts_active(self):
        measure = VBTSMeasure(
            symbol="THYAO",
            tier=2,
            description="Kredili işlem yasağı",
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        checker = BISTRegulatoryChecker(vbts_measures=[measure])
        active = checker.check_vbts_measures("THYAO")
        assert len(active) >= 1
        assert checker.is_vbts_restricted("THYAO") is True

    def test_vbts_inactive(self):
        measure = VBTSMeasure(
            symbol="THYAO",
            tier=2,
            description="Eski tedbir",
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            end_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        checker = BISTRegulatoryChecker(vbts_measures=[measure])
        active = checker.check_vbts_measures("THYAO")
        assert len(active) == 0
        assert checker.is_vbts_restricted("THYAO") is False

    def test_validate_trade_all_clear(self):
        checker = BISTRegulatoryChecker()
        result = checker.validate_trade(
            symbol="THYAO",
            price=105.0,
            reference_price=100.0,
            index_level=10000,
            index_previous_close=10000,
            orders_today=30,
            trades_today=10,
            position_value=100_000,
            cash=25_000,
            side="BUY",
        )
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_trade_cb_fail(self):
        checker = BISTRegulatoryChecker()
        result = checker.validate_trade(
            symbol="THYAO",
            price=130.0,
            reference_price=100.0,
            index_level=10000,
            index_previous_close=10000,
            orders_today=30,
            trades_today=10,
            position_value=100_000,
            cash=25_000,
            side="BUY",
        )
        assert result["valid"] is False
        assert any("Price" in e for e in result["errors"])

    def test_position_tracking(self):
        checker = BISTRegulatoryChecker()
        assert checker.get_position("THYAO") == 0.0
        checker.update_position("THYAO", "BUY", 100)
        assert checker.get_position("THYAO") == 100.0
        checker.update_position("THYAO", "SELL", 30)
        assert checker.get_position("THYAO") == 70.0

    def test_short_selling_no_position(self):
        checker = BISTRegulatoryChecker()
        result = checker.check_short_selling("THYAO", "SELL", 10)
        assert result["allowed"] is False
        assert "No long position" in result["reason"]

    def test_short_selling_exceeds_position(self):
        checker = BISTRegulatoryChecker()
        checker.update_position("THYAO", "BUY", 50)
        result = checker.check_short_selling("THYAO", "SELL", 60)
        assert result["allowed"] is False
        assert "exceeds long position" in result["reason"]

    def test_short_selling_closing_position(self):
        checker = BISTRegulatoryChecker()
        checker.update_position("THYAO", "BUY", 50)
        result = checker.check_short_selling("THYAO", "SELL", 30)
        assert result["allowed"] is True

    def test_validate_trade_short_selling_blocked(self):
        checker = BISTRegulatoryChecker()
        result = checker.validate_trade(
            symbol="THYAO",
            price=105.0,
            reference_price=100.0,
            index_level=10000,
            index_previous_close=10000,
            orders_today=30,
            trades_today=10,
            position_value=0,
            cash=25_000,
            side="SELL",
            size=10,
        )
        assert result["valid"] is False
        assert any("short" in e.lower() or "No long" in e for e in result["errors"])

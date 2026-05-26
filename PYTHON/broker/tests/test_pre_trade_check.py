"""
tests/test_pre_trade_check.py — On-ticaret risk birim testleri
"""
import pytest
from decimal import Decimal

from broker.risk.pre_trade_check import PreTradeRiskChecker
from broker.core.broker_interface import Order, OrderSide, OrderType


class TestPreTradeRiskChecker:
    def test_allowed(self):
        checker = PreTradeRiskChecker()
        order = Order(symbol="THYAO", side=OrderSide.BUY, quantity=Decimal("10"),
                      price=Decimal("100"), order_type=OrderType.LIMIT)
        result = checker.check(order, current_position=Decimal("0"), portfolio_value=Decimal("100000"), daily_pnl=Decimal("0"))
        assert result.allowed is True
        assert result.latency_us >= 0

    def test_position_limit_reject(self):
        checker = PreTradeRiskChecker(max_position_pct=0.02)
        order = Order(symbol="THYAO", side=OrderSide.BUY, quantity=Decimal("5000"),
                      price=Decimal("100"), order_type=OrderType.LIMIT)
        result = checker.check(order, current_position=Decimal("0"), portfolio_value=Decimal("100000"), daily_pnl=Decimal("0"))
        assert result.allowed is False
        assert any("K94" in e for e in result.errors)

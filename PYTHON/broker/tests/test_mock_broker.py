"""
tests/test_mock_broker.py — MockBroker birim testleri
"""
import pytest
import asyncio
from decimal import Decimal

from broker.adapters.mock_broker import MockBroker
from broker.core.broker_interface import Order, OrderSide, OrderType


class TestMockBroker:
    @pytest.fixture
    def broker(self):
        return MockBroker(fill_delay_ms=0, partial_fill_prob=0.0)

    def test_connect(self, broker):
        result = asyncio.run(broker.connect())
        assert result is True

    def test_place_order(self, broker):
        order = Order(symbol="THYAO", side=OrderSide.BUY, quantity=Decimal("100"),
                      price=Decimal("100"), order_type=OrderType.LIMIT)
        report = asyncio.run(broker.place_order(order))
        assert report.status.value in ["FILLED", "PARTIAL"]

    def test_positions_update(self, broker):
        order = Order(symbol="THYAO", side=OrderSide.BUY, quantity=Decimal("50"),
                      price=Decimal("100"), order_type=OrderType.LIMIT)
        asyncio.run(broker.place_order(order))
        positions = asyncio.run(broker.get_positions())
        assert positions.get("THYAO", Decimal("0")) >= Decimal("50")

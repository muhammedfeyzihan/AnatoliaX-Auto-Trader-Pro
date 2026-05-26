"""
adapters/mock_broker.py — Deterministik test aracisi
"""
from decimal import Decimal
from typing import Dict

from broker.core.broker_interface import BrokerInterface, ExecutionReport, Order, OrderStatus


class MockBroker(BrokerInterface):
    """
    Deterministik test aracisi: kayitli emirleri bellekte tutar.

    Kullanim:
        broker = MockBroker(fill_delay_ms=50, partial_fill_prob=0.1)
        report = await broker.place_order(order)
    """

    def __init__(self, fill_delay_ms: float = 50.0, partial_fill_prob: float = 0.1):
        self._orders: Dict[str, Order] = {}
        self._reports: Dict[str, ExecutionReport] = {}
        self._positions: Dict[str, Decimal] = {}
        self._cash = Decimal("100000")
        self._fill_delay_ms = fill_delay_ms
        self._partial_fill_prob = partial_fill_prob
        self._seq = 0

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def place_order(self, order: Order) -> ExecutionReport:
        self._seq += 1
        oid = f"MOCK-{self._seq}"
        self._orders[oid] = order
        import random
        status = OrderStatus.FILLED if random.random() > self._partial_fill_prob else OrderStatus.PARTIAL
        filled = order.quantity if status == OrderStatus.FILLED else order.quantity / Decimal("2")
        avg = order.price or Decimal("100")
        report = ExecutionReport(
            order_id=oid,
            status=status,
            filled_qty=filled,
            avg_price=avg,
            commission=Decimal("0.4"),
            timestamp="2026-05-26T12:00:00Z",
        )
        self._reports[oid] = report
        # Pozisyon guncelle
        pos = self._positions.get(order.symbol, Decimal("0"))
        if order.side.value == "BUY":
            self._positions[order.symbol] = pos + filled
            self._cash -= filled * avg
        else:
            self._positions[order.symbol] = pos - filled
            self._cash += filled * avg
        return report

    async def cancel_order(self, order_id: str) -> bool:
        return order_id in self._orders

    async def get_positions(self) -> Dict[str, Decimal]:
        return dict(self._positions)

    async def get_cash(self) -> Decimal:
        return self._cash

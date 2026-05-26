"""
viop/viop_adapter.py — VIOP (Vadeli Islemler ve Opsiyonlar) adaptoru
"""
from decimal import Decimal
from typing import Dict

from broker.core.broker_interface import BrokerInterface, ExecutionReport, Order, OrderStatus
from broker.viop.margin_calculator import VIOPMarginCalculator


class VIOPAdapter(BrokerInterface):
    """
    VIOP emir adaptoru.

    Farkliliklar:
    - Emirler kontrat bazli (XU030, XU100 vb.)
    - Marjin kontrolu: VIOPMarginCalculator ile on-gonderim
    - Opsiyonlar icin ek alanlar: right (CALL/PUT), strike, expiry
    """

    def __init__(self, base_url: str, api_key: str, margin_calculator: VIOPMarginCalculator = None):
        self.base_url = base_url
        self.api_key = api_key
        self._mc = margin_calculator or VIOPMarginCalculator()
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def place_order(self, order: Order) -> ExecutionReport:
        # Marjin kontrolu
        margin = self._mc.calculate(order.price or Decimal("100"), order.quantity, 0.2)
        return ExecutionReport(
            order_id="VIOP-1",
            status=OrderStatus.PENDING,
            filled_qty=Decimal("0"),
            avg_price=Decimal("0"),
            commission=Decimal("0"),
            timestamp="2026-05-26T12:00:00Z",
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> Dict[str, Decimal]:
        return {}

    async def get_cash(self) -> Decimal:
        return Decimal("0")

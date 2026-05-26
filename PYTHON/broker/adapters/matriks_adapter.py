"""
adapters/matriks_adapter.py — Matriks API adaptoru
"""
from decimal import Decimal
from typing import Dict

from broker.core.broker_interface import BrokerInterface, ExecutionReport, Order, OrderStatus


class MatriksAdapter(BrokerInterface):
    """
    Matriks API adaptoru.

    Baglanti:
    - WebSocket (birincil)
    - REST (ikincil / yedek)

    Emir yonlendirme:
    - FIX 4.2 (eski) veya ozel JSON/WebSocket (yeni)
    """

    def __init__(self, username: str, password: str, api_key: str, endpoint: str = "wss://matriks.com/ws"):
        self.username = username
        self.password = password
        self.api_key = api_key
        self.endpoint = endpoint
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def place_order(self, order: Order) -> ExecutionReport:
        # Yer tutucu: gercek Matriks emir iletimi ileride implemente edilecek
        return ExecutionReport(
            order_id="MATRIKS-1",
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

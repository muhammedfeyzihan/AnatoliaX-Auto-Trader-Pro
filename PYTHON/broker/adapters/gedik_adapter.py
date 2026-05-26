"""
adapters/gedik_adapter.py — Gedik Yatirim API adaptoru
"""
from decimal import Decimal
from typing import Dict

from broker.core.broker_interface import BrokerInterface, ExecutionReport, Order, OrderStatus


class GedikAdapter(BrokerInterface):
    """
    Gedik Yatirim API adaptoru.

    Baglanti:
    - REST (birincil)
    - FIX (kurumsal musteriler icin)
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.gedik.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def place_order(self, order: Order) -> ExecutionReport:
        return ExecutionReport(
            order_id="GEDIK-1",
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

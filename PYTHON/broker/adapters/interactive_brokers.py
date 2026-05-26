"""
adapters/interactive_brokers.py — Interactive Brokers TWS API adaptoru
"""
from decimal import Decimal
from typing import Dict

from broker.core.broker_interface import BrokerInterface, ExecutionReport, Order, OrderStatus


class InteractiveBrokersAdapter(BrokerInterface):
    """
    Interactive Brokers TWS API adaptoru.

    IB TWS: global piyasalar (BIST harici de kullanilabilir).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def place_order(self, order: Order) -> ExecutionReport:
        return ExecutionReport(order_id="IB-1", status=OrderStatus.PENDING,
                               filled_qty=Decimal("0"), avg_price=Decimal("0"),
                               commission=Decimal("0"), timestamp="2026-05-26T12:00:00Z")

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> Dict[str, Decimal]:
        return {}

    async def get_cash(self) -> Decimal:
        return Decimal("0")

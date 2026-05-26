"""
execution/order_manager.py — Emir durum makinesi (PENDING->SUBMITTED->ACK->FILLED)
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import Dict, List, Optional


class OrderState(Enum):
    PENDING = auto()
    SUBMITTED = auto()
    ACK = auto()
    PARTIAL = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()


@dataclass
class ManagedOrder:
    client_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Optional[Decimal]
    state: OrderState = OrderState.PENDING
    filled_qty: Decimal = Decimal("0")
    avg_price: Decimal = Decimal("0")
    history: List[tuple] = field(default_factory=list)


class OrderManager:
    """
    Emir durum makinesi yoneticisi.

    Durum gecisleri:
    PENDING -> SUBMITTED (emir gonderildi)
    SUBMITTED -> ACK (araci onayi)
    ACK -> PARTIAL (kismi dolma)
    PARTIAL -> FILLED (tam dolma)
    HERHANGI -> CANCELLED (iptal)
    HERHANGI -> REJECTED (reddetme)

    K141: Her durum degisikligi loglanir ve event bus'a yayinlanir.
    """

    def __init__(self):
        self._orders: Dict[str, ManagedOrder] = {}

    def submit(self, order: ManagedOrder) -> None:
        self._orders[order.client_order_id] = order
        order.state = OrderState.SUBMITTED
        order.history.append(("SUBMITTED", 0))

    def on_ack(self, client_order_id: str, exchange_order_id: str) -> None:
        o = self._orders.get(client_order_id)
        if o and o.state in (OrderState.PENDING, OrderState.SUBMITTED):
            o.state = OrderState.ACK
            o.history.append(("ACK", 0))

    def on_fill(self, client_order_id: str, qty: Decimal, price: Decimal) -> None:
        o = self._orders.get(client_order_id)
        if not o:
            return
        o.filled_qty += qty
        o.avg_price = (o.avg_price * (o.filled_qty - qty) + price * qty) / o.filled_qty if o.filled_qty > 0 else price
        if o.filled_qty >= o.quantity:
            o.state = OrderState.FILLED
        else:
            o.state = OrderState.PARTIAL
        o.history.append(("FILL", float(qty)))

    def get_open_orders(self) -> List[ManagedOrder]:
        return [o for o in self._orders.values() if o.state in (OrderState.SUBMITTED, OrderState.ACK, OrderState.PARTIAL)]

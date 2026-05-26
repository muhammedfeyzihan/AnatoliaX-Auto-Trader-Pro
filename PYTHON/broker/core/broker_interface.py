"""
core/broker_interface.py — Broker soyut arayuzu
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Dict, List, Optional


class OrderSide(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP = auto()
    STOP_LIMIT = auto()
    ICEBERG = auto()


class TimeInForce(Enum):
    DAY = auto()
    IOC = auto()
    FOK = auto()
    GTD = auto()


class OrderStatus(Enum):
    PENDING = auto()
    OPEN = auto()
    PARTIAL = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal]
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    client_order_id: str = ""


@dataclass
class ExecutionReport:
    order_id: str
    status: OrderStatus
    filled_qty: Decimal
    avg_price: Decimal
    commission: Decimal
    timestamp: str


class BrokerInterface(ABC):
    """
    BIST araci kurumlari icin soyut arayuz.

    Uygulamalar:
    - MatriksAdapter
    - GedikAdapter
    - IsYatirimAdapter
    - MockBroker (test)
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Araciya baglan; oturum ac."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Baglantiyi duzgun kapat."""
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> ExecutionReport:
        """Emir gonder; ExecutionReport dondur."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Emri iptal et; basari dondur."""
        pass

    @abstractmethod
    async def get_positions(self) -> Dict[str, Decimal]:
        """Acik pozisyonlari dondur."""
        pass

    @abstractmethod
    async def get_cash(self) -> Decimal:
        """Nakit bakiyeyi dondur."""
        pass

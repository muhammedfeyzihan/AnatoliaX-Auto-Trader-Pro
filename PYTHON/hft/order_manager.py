"""
order_manager.py — HFT order lifecycle with queue position awareness.
Tracks pending orders, partial fills, and cancellations.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class HFTOrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class HFTOrder:
    order_id: str
    symbol: str
    side: str  # BUY / SELL
    size: float
    price: float
    order_type: str = "limit"
    status: HFTOrderStatus = HFTOrderStatus.PENDING
    filled_size: float = 0.0
    avg_fill_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    submitted_at: Optional[float] = None
    filled_at: Optional[float] = None


class HFTOrderManager:
    """
    Manages HFT order lifecycle.
    - Tracks pending/submitted/filled orders
    - Computes queue position (simulated)
    - Auto-cancel stale orders
    """

    def __init__(self, max_pending_ttl_seconds: float = 5.0):
        self.max_pending_ttl = max_pending_ttl_seconds
        self._orders: Dict[str, HFTOrder] = {}
        self._fills: List[dict] = []

    def create_order(self, order_id: str, symbol: str, side: str, size: float, price: float, order_type: str = "limit") -> HFTOrder:
        order = HFTOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            order_type=order_type,
        )
        self._orders[order_id] = order
        return order

    def submit(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None:
            return False
        order.status = HFTOrderStatus.SUBMITTED
        order.submitted_at = time.time()
        return True

    def fill(self, order_id: str, filled_size: float, fill_price: float):
        order = self._orders.get(order_id)
        if order is None:
            return

        order.filled_size += filled_size
        # Update avg fill price
        total_value = (order.avg_fill_price * (order.filled_size - filled_size)) + (fill_price * filled_size)
        order.avg_fill_price = total_value / order.filled_size if order.filled_size > 0 else 0.0

        if order.filled_size >= order.size:
            order.status = HFTOrderStatus.FILLED
            order.filled_at = time.time()
        else:
            order.status = HFTOrderStatus.PARTIAL_FILL

        self._fills.append({
            "order_id": order_id,
            "symbol": order.symbol,
            "side": order.side,
            "filled_size": filled_size,
            "fill_price": fill_price,
            "timestamp": time.time(),
        })

    def cancel(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None or order.status in (HFTOrderStatus.FILLED, HFTOrderStatus.CANCELLED):
            return False
        order.status = HFTOrderStatus.CANCELLED
        return True

    def cancel_stale(self) -> List[str]:
        """Cancel orders that have been pending/submitted too long."""
        now = time.time()
        cancelled = []
        for oid, order in self._orders.items():
            if order.status in (HFTOrderStatus.PENDING, HFTOrderStatus.SUBMITTED):
                age = now - order.created_at
                if age > self.max_pending_ttl:
                    order.status = HFTOrderStatus.CANCELLED
                    cancelled.append(oid)
        return cancelled

    def get_open_orders(self, symbol: Optional[str] = None) -> List[HFTOrder]:
        open_status = {HFTOrderStatus.PENDING, HFTOrderStatus.SUBMITTED, HFTOrderStatus.PARTIAL_FILL}
        orders = [o for o in self._orders.values() if o.status in open_status]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_order(self, order_id: str) -> Optional[HFTOrder]:
        return self._orders.get(order_id)

    def queue_position_estimate(self, order_id: str, book_depth: float = 0.0) -> float:
        """
        Estimate queue position as a fraction of book depth.
        0.0 = front of queue, 1.0 = back.
        Simplified model; real implementation would use actual order book.
        """
        order = self._orders.get(order_id)
        if order is None or order.status != HFTOrderStatus.SUBMITTED:
            return 0.0
        if book_depth <= 0:
            return 0.5
        # Simulated: newer orders are further back
        age = time.time() - (order.submitted_at or time.time())
        # Approximate queue position based on age
        return min(age / 2.0, 1.0)  # Simplified heuristic

    def stats(self) -> dict:
        statuses = [o.status for o in self._orders.values()]
        return {
            "total_orders": len(self._orders),
            "filled": statuses.count(HFTOrderStatus.FILLED),
            "cancelled": statuses.count(HFTOrderStatus.CANCELLED),
            "rejected": statuses.count(HFTOrderStatus.REJECTED),
            "pending": statuses.count(HFTOrderStatus.PENDING),
            "total_fills": len(self._fills),
        }

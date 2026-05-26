"""
execution/order_state_machine.py — Institutional Order State Machine (Phase 1)
Module 3 from anatoliax_prompt_v6.txt

Features:
  - Order lifecycle: S = {PENDING, SUBMITTED, PARTIAL_FILL, FILLED, CANCELLED, EXPIRED, ERROR}
  - Transition matrix T: P(S_t+1 | S_t, event)
  - Partial fill handling, retry with exponential backoff+jitter, TTL eviction, broker failover, idempotency keys.
"""

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable


class OrderState(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


@dataclass
class OrderTransition:
    order_id: str
    from_state: OrderState
    to_state: OrderState
    event: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_attempt: int = 0


class OrderStateMachine:
    """
    Full order lifecycle with transition matrix, retry logic, TTL cleanup, failover, idempotency.
    """

    # Transition matrix: (current_state, event) -> next_state
    TRANSITIONS: Dict[tuple, OrderState] = {
        (OrderState.PENDING, "submit"): OrderState.SUBMITTED,
        (OrderState.PENDING, "error"): OrderState.ERROR,
        (OrderState.PENDING, "cancel"): OrderState.CANCELLED,
        (OrderState.SUBMITTED, "partial_fill"): OrderState.PARTIAL_FILL,
        (OrderState.SUBMITTED, "fill"): OrderState.FILLED,
        (OrderState.SUBMITTED, "cancel"): OrderState.CANCELLED,
        (OrderState.SUBMITTED, "expire"): OrderState.EXPIRED,
        (OrderState.SUBMITTED, "error"): OrderState.ERROR,
        (OrderState.PARTIAL_FILL, "fill"): OrderState.FILLED,
        (OrderState.PARTIAL_FILL, "cancel"): OrderState.CANCELLED,
        (OrderState.PARTIAL_FILL, "expire"): OrderState.EXPIRED,
        (OrderState.ERROR, "retry"): OrderState.PENDING,
        (OrderState.CANCELLED, "resubmit"): OrderState.PENDING,
        (OrderState.EXPIRED, "resubmit"): OrderState.PENDING,
    }

    def __init__(
        self,
        max_retries: int = 3,
        base_retry_sec: float = 1.0,
        max_age_sec: float = 300.0,
        broker_health_check: Optional[Callable[[], bool]] = None,
    ):
        self.max_retries = max_retries
        self.base_retry_sec = base_retry_sec
        self.max_age_sec = max_age_sec
        self.broker_health_check = broker_health_check

        self._orders: Dict[str, dict] = {}
        self._transitions: List[OrderTransition] = []
        self._idempotency_keys: set = set()

    def _idempotency_key(self, order_id: str, timestamp_ns: int) -> str:
        nonce = uuid.uuid4().hex[:8]
        key = f"{order_id}:{timestamp_ns}:{nonce}"
        self._idempotency_keys.add(key)
        return key

    def create_order(self, order_id: str, symbol: str, side: str, size: float, price: float) -> dict:
        ts = int(datetime.now(timezone.utc).timestamp() * 1e9)
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "state": OrderState.PENDING,
            "filled_size": 0.0,
            "avg_fill_price": 0.0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "retry_count": 0,
            "idempotency_key": self._idempotency_key(order_id, ts),
        }
        self._orders[order_id] = order
        return order

    def transition(self, order_id: str, event: str, payload: Optional[dict] = None) -> OrderState:
        order = self._orders.get(order_id)
        if not order:
            return OrderState.ERROR

        current = order["state"]
        next_state = self.TRANSITIONS.get((current, event), current)

        if next_state == OrderState.FILLED and payload:
            order["filled_size"] = payload.get("filled_size", order["size"])
            order["avg_fill_price"] = payload.get("avg_price", order["price"])
        elif next_state == OrderState.PARTIAL_FILL and payload:
            order["filled_size"] = payload.get("filled_size", 0.0)
            order["avg_fill_price"] = payload.get("avg_price", order["price"])

        order["state"] = next_state
        order["updated_at"] = datetime.now(timezone.utc)

        self._transitions.append(OrderTransition(
            order_id=order_id,
            from_state=current,
            to_state=next_state,
            event=event,
            retry_attempt=order["retry_count"],
        ))
        return next_state

    def retry(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order or order["retry_count"] >= self.max_retries:
            return False

        backoff = self.base_retry_sec * (2 ** order["retry_count"]) * random.uniform(0.5, 1.5)
        if backoff > 0.001:
            time.sleep(backoff)
        order["retry_count"] += 1
        self.transition(order_id, "retry")
        return True

    def evict_stale(self) -> List[str]:
        now = datetime.now(timezone.utc)
        evicted = []
        for oid, order in list(self._orders.items()):
            if (now - order["created_at"]).total_seconds() > self.max_age_sec:
                if order["state"] not in (OrderState.FILLED, OrderState.CANCELLED):
                    order["state"] = OrderState.EXPIRED
                    evicted.append(oid)
        return evicted

    def failover(self, order_id: str, backup_broker: Callable) -> bool:
        order = self._orders.get(order_id)
        if not order:
            return False
        if self.broker_health_check and not self.broker_health_check():
            try:
                backup_broker(order)
                return True
            except Exception:
                pass
        return False

    def reconcile(self, order_id: str, target_size: float, epsilon: float = 1e-6) -> bool:
        order = self._orders.get(order_id)
        if not order:
            return False
        return abs(order["filled_size"] - target_size) <= epsilon

    def get_order(self, order_id: str) -> Optional[dict]:
        return self._orders.get(order_id)

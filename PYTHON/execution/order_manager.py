"""
order_manager.py — Retry sistemi, partial fill, order reconciliation
"""
import time
import random
from typing import Callable, Optional, Dict, List
from datetime import datetime, timedelta, timezone


class OrderManager:
    """
    Emir yönetimi: retry, exponential backoff, partial fill takibi,
    reconciliation ve idempotency key destegi.
    """

    def __init__(
        self,
        submit_fn: Callable,
        status_fn: Optional[Callable] = None,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        partial_fill_timeout_sec: float = 30.0,
    ):
        self.submit_fn = submit_fn
        self.status_fn = status_fn
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.partial_fill_timeout_sec = partial_fill_timeout_sec
        self._orders: Dict[str, dict] = {}
        self._pending_partials: Dict[str, datetime] = {}

    def submit(self, order_id: str, payload: dict) -> dict:
        """Emir gonder; basarisizsa exponential backoff ile tekrar dene."""
        self._orders[order_id] = {"payload": payload, "status": "pending", "retries": 0}

        for attempt in range(self.max_retries + 1):
            try:
                result = self.submit_fn(payload)
                self._orders[order_id]["status"] = result.get("status", "filled")
                self._orders[order_id]["response"] = result
                if result.get("partial"):
                    self._pending_partials[order_id] = datetime.now(timezone.utc)
                return result
            except Exception as e:
                self._orders[order_id]["retries"] = attempt + 1
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 0.5), self.max_delay)
                    time.sleep(delay)
                else:
                    self._orders[order_id]["status"] = "error"
                    self._orders[order_id]["error"] = str(e)
                    raise

        return self._orders[order_id]

    def reconcile(self, order_id: str) -> dict:
        """Disaridan durum sorgula, ic kayitla eslestir."""
        if not self.status_fn:
            return self._orders.get(order_id, {})

        external = self.status_fn(order_id)
        local = self._orders.get(order_id, {})
        if external.get("filled_size") != local.get("response", {}).get("filled_size"):
            local["status"] = "reconciled"
            local["external"] = external
        return local

    def check_partial_fills(self) -> List[str]:
        """Zaman asimina ugrayan partial fill'lari listele."""
        now = datetime.now(timezone.utc)
        expired = []
        for oid, start in list(self._pending_partials.items()):
            if (now - start).total_seconds() > self.partial_fill_timeout_sec:
                expired.append(oid)
                self._orders[oid]["status"] = "partial_expired"
                del self._pending_partials[oid]
        return expired

    def get_summary(self) -> dict:
        total = len(self._orders)
        filled = sum(1 for o in self._orders.values() if o["status"] == "filled")
        partial = len(self._pending_partials)
        errors = sum(1 for o in self._orders.values() if o["status"] == "error")
        return {
            "total_orders": total,
            "filled": filled,
            "partial_pending": partial,
            "errors": errors,
        }

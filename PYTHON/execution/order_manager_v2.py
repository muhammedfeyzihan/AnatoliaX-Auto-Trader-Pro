"""
order_manager_v2.py — Robust Order Management: retry, stale recovery, slippage protection.
K221-K223: OrderManagerV2.
"""
import time
import random
from typing import Callable, Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone
from enum import Enum


class OrderStatusV2(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    STALE = "STALE"
    ERROR = "ERROR"


class OrderManagerV2:
    """
    Gelistirilmis emir yoneticisi: retry, stale recovery, slippage korumasi.
    """

    def __init__(
        self,
        submit_fn: Callable,
        status_fn: Optional[Callable] = None,
        cancel_fn: Optional[Callable] = None,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        partial_fill_timeout_sec: float = 30.0,
        stale_threshold_sec: float = 60.0,
        slippage_tolerance_pct: float = 0.01,
        on_event: Optional[Callable] = None,
    ):
        self.submit_fn = submit_fn
        self.status_fn = status_fn
        self.cancel_fn = cancel_fn
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.partial_fill_timeout_sec = partial_fill_timeout_sec
        self.stale_threshold_sec = stale_threshold_sec
        self.slippage_tolerance_pct = slippage_tolerance_pct
        self.on_event = on_event
        self._orders: Dict[str, dict] = {}
        self._pending_partials: Dict[str, datetime] = {}

    def submit(self, order_id: str, payload: dict) -> Dict:
        """Emir gonder; retry + slippage kontrolu."""
        requested_price = payload.get("price", 0)
        self._orders[order_id] = {
            "payload": payload,
            "status": OrderStatusV2.PENDING.value,
            "retries": 0,
            "created_at": datetime.now(timezone.utc),
            "requested_price": requested_price,
        }

        for attempt in range(self.max_retries + 1):
            try:
                result = self.submit_fn(payload)
                status = result.get("status", "filled")
                self._orders[order_id]["status"] = status
                self._orders[order_id]["response"] = result
                self._orders[order_id]["filled_price"] = result.get("price", requested_price)

                # Slippage check
                if requested_price and status in ("filled", "FILLED"):
                    slippage = abs(result.get("price", requested_price) - requested_price) / requested_price if requested_price else 0
                    if slippage > self.slippage_tolerance_pct:
                        self._orders[order_id]["slippage_alert"] = f"Slippage %{slippage*100:.2f} > %{self.slippage_tolerance_pct*100}"
                        self._emit("SLIPPAGE_ALERT", order_id, self._orders[order_id])

                if result.get("partial") or status == "PARTIAL":
                    self._pending_partials[order_id] = datetime.now(timezone.utc)

                self._emit("SUBMITTED", order_id, self._orders[order_id])
                return result
            except Exception as e:
                self._orders[order_id]["retries"] = attempt + 1
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 0.5), self.max_delay)
                    time.sleep(delay)
                else:
                    self._orders[order_id]["status"] = OrderStatusV2.ERROR.value
                    self._orders[order_id]["error"] = str(e)
                    self._emit("ERROR", order_id, self._orders[order_id])
                    raise

        return self._orders[order_id]

    def reconcile(self, order_id: str) -> Dict:
        """Dis kaynakla eslestir."""
        if not self.status_fn:
            return self._orders.get(order_id, {})
        try:
            external = self.status_fn(order_id)
        except Exception:
            return self._orders.get(order_id, {})

        local = self._orders.get(order_id, {})
        local_status = local.get("status", "")
        ext_status = external.get("status", "")

        if ext_status and ext_status != local_status:
            local["status"] = ext_status
            local["reconciled_at"] = datetime.now(timezone.utc).isoformat()
            self._emit("RECONCILED", order_id, local)

        if external.get("filled_size") != local.get("response", {}).get("filled_size"):
            local["external"] = external

        return local

    def check_stale_orders(self) -> List[str]:
        """Zamani gecmis emirleri bul."""
        now = datetime.now(timezone.utc)
        stale = []
        for oid, data in list(self._orders.items()):
            created = data.get("created_at")
            if not created:
                continue
            elapsed = (now - created).total_seconds()
            if elapsed > self.stale_threshold_sec and data["status"] not in ("filled", "FILLED", "cancelled", "CANCELLED", "rejected", "REJECTED"):
                stale.append(oid)
                data["status"] = OrderStatusV2.STALE.value
                self._emit("STALE", oid, data)
                if self.cancel_fn:
                    try:
                        self.cancel_fn(oid)
                    except Exception:
                        pass
        return stale

    def check_partial_fills(self) -> List[str]:
        """Partial fill timeout kontrolu."""
        now = datetime.now(timezone.utc)
        expired = []
        for oid, start in list(self._pending_partials.items()):
            if (now - start).total_seconds() > self.partial_fill_timeout_sec:
                expired.append(oid)
                self._orders[oid]["status"] = OrderStatusV2.STALE.value
                del self._pending_partials[oid]
                self._emit("PARTIAL_EXPIRED", oid, self._orders[oid])
        return expired

    def cancel(self, order_id: str) -> bool:
        if self.cancel_fn:
            try:
                self.cancel_fn(order_id)
                self._orders[order_id]["status"] = OrderStatusV2.CANCELLED.value
                self._emit("CANCELLED", order_id, self._orders[order_id])
                return True
            except Exception:
                pass
        return False

    def get_summary(self) -> Dict:
        total = len(self._orders)
        filled = sum(1 for o in self._orders.values() if o["status"] in ("filled", "FILLED"))
        partial = len(self._pending_partials)
        errors = sum(1 for o in self._orders.values() if o["status"] in ("error", "ERROR"))
        stale = sum(1 for o in self._orders.values() if o["status"] == OrderStatusV2.STALE.value)
        return {
            "total_orders": total,
            "filled": filled,
            "partial_pending": partial,
            "errors": errors,
            "stale": stale,
        }

    def get_order(self, order_id: str) -> Optional[Dict]:
        return self._orders.get(order_id)

    def _emit(self, event_type: str, order_id: str, data: dict):
        if self.on_event:
            self.on_event(event_type, order_id, data)

    def reset(self):
        self._orders.clear()
        self._pending_partials.clear()

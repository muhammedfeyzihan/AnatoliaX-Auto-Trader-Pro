"""
contingency_manager.py — Local emulation of advanced order types.
BIST brokers typically only support MARKET/LIMIT natively.
This module tracks parent/child relationships and emulates
BRACKET, OCO, TRAILING_STOP, and ICEBERG orders locally.
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
from execution.order_types import (
    BracketOrder, OCOOrder, TrailingStopOrder, IcebergOrder, OrderType, TimeInForce,
)


class ContingencyManager:
    """
    Tracks parent-child order relationships and emulates advanced order types
    by converting them to simple MARKET/LIMIT orders for the broker,
    while managing the contingent logic locally.
    """

    def __init__(self, on_broker_submit: Optional[Callable] = None):
        self.on_broker_submit = on_broker_submit
        self._brackets: Dict[str, dict] = {}
        self._ocos: Dict[str, dict] = {}
        self._trailings: Dict[str, TrailingStopOrder] = {}
        self._icebergs: Dict[str, dict] = {}
        self._next_id = 1

    def _gen_id(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}_{self._next_id}"

    def submit_bracket(self, bracket: BracketOrder) -> dict:
        """
        Submit a bracket order.
        1. Send entry order to broker.
        2. Track TP and SL locally; activate when entry fills.
        Returns: {"entry_id": str, "tp_id": str, "sl_id": str, "status": str}
        """
        parent_id = self._gen_id("BR")
        entry_id = self._gen_id("ENT")

        # Entry order goes to broker
        entry_order = {
            "id": entry_id,
            "symbol": bracket.symbol,
            "side": bracket.side,
            "size": bracket.size,
            "price": bracket.entry_price,
            "order_type": bracket.entry_type.value,
            "tif": bracket.time_in_force.value,
        }

        # TP and SL tracked locally
        tp_id = self._gen_id("TP")
        sl_id = self._gen_id("SL")

        self._brackets[parent_id] = {
            "entry_id": entry_id,
            "tp_id": tp_id,
            "sl_id": sl_id,
            "symbol": bracket.symbol,
            "side": bracket.side,
            "size": bracket.size,
            "entry_price": bracket.entry_price,
            "tp_price": bracket.tp_price,
            "sl_price": bracket.sl_price,
            "trailing_distance": bracket.trailing_distance,
            "status": "PENDING",
            "entry_filled": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.on_broker_submit:
            self.on_broker_submit(entry_order)

        return {
            "parent_id": parent_id,
            "entry_id": entry_id,
            "tp_id": tp_id,
            "sl_id": sl_id,
            "status": "PENDING",
        }

    def on_fill(self, order_id: str, filled_size: float, avg_price: float):
        """Called when any order fills. Activate contingent logic."""
        # Check brackets
        for parent_id, bracket in self._brackets.items():
            if bracket["entry_id"] == order_id and not bracket["entry_filled"]:
                bracket["entry_filled"] = True
                bracket["status"] = "ACTIVE"
                bracket["avg_fill_price"] = avg_price
                bracket["remaining_size"] = filled_size
                # If trailing distance set, convert SL to trailing
                if bracket.get("trailing_distance"):
                    self._trailings[bracket["sl_id"]] = TrailingStopOrder(
                        symbol=bracket["symbol"],
                        side="SELL" if bracket["side"] == "BUY" else "BUY",
                        size=bracket["size"],
                        distance=bracket["trailing_distance"],
                        current_stop=bracket["sl_price"],
                    )
                break

        # Check OCO
        for parent_id, oco in self._ocos.items():
            if order_id in (oco["leg_a_id"], oco["leg_b_id"]):
                oco["status"] = "FILLED"
                # Cancel the other leg
                other_id = oco["leg_b_id"] if order_id == oco["leg_a_id"] else oco["leg_a_id"]
                oco["cancelled_id"] = other_id
                break

        # Check iceberg slices
        for parent_id, ice in self._icebergs.items():
            if order_id in ice["slice_ids"]:
                ice["filled_slices"].append(order_id)
                ice["remaining"] -= filled_size
                self._maybe_advance_iceberg(parent_id)
                break

    def submit_oco(self, oco: OCOOrder) -> dict:
        """Submit an OCO order (two legs, one cancels the other)."""
        parent_id = self._gen_id("OCO")
        leg_a_id = self._gen_id("LEG")
        leg_b_id = self._gen_id("LEG")

        self._ocos[parent_id] = {
            "leg_a_id": leg_a_id,
            "leg_b_id": leg_b_id,
            "symbol": oco.symbol,
            "side": oco.side,
            "size": oco.size,
            "status": "PENDING",
        }

        orders = []
        if oco.limit_price:
            orders.append({
                "id": leg_a_id,
                "symbol": oco.symbol,
                "side": oco.side,
                "size": oco.size,
                "price": oco.limit_price,
                "order_type": "limit",
            })
        if oco.stop_price:
            orders.append({
                "id": leg_b_id,
                "symbol": oco.symbol,
                "side": oco.side,
                "size": oco.size,
                "price": oco.stop_price,
                "order_type": "stop_market",
            })

        for o in orders:
            if self.on_broker_submit:
                self.on_broker_submit(o)

        return {
            "parent_id": parent_id,
            "leg_a_id": leg_a_id,
            "leg_b_id": leg_b_id,
            "status": "PENDING",
        }

    def submit_trailing_stop(self, ts: TrailingStopOrder) -> dict:
        """Track a trailing stop order locally."""
        order_id = self._gen_id("TS")
        self._trailings[order_id] = ts
        return {"id": order_id, "status": "ACTIVE"}

    def update_trailing(self, order_id: str, current_price: float, is_long: bool = True):
        """Update trailing stop price based on market movement."""
        ts = self._trailings.get(order_id)
        if not ts:
            return None
        ts.update_stop(current_price, is_long=is_long)
        # Check if triggered
        if is_long and current_price <= ts.current_stop:
            return {"triggered": True, "stop_price": ts.current_stop, "id": order_id}
        if not is_long and current_price >= ts.current_stop:
            return {"triggered": True, "stop_price": ts.current_stop, "id": order_id}
        return {"triggered": False, "stop_price": ts.current_stop, "id": order_id}

    def submit_iceberg(self, iceberg: IcebergOrder) -> dict:
        """Split iceberg into slices. Only first slice goes to broker immediately."""
        parent_id = self._gen_id("IB")
        slices = []
        remaining = iceberg.total_size
        while remaining > 0:
            slice_size = min(iceberg.display_qty, remaining)
            sid = self._gen_id("SL")
            slices.append(sid)
            if self.on_broker_submit and len(slices) == 1:
                # First slice only; rest sent after fill
                self.on_broker_submit({
                    "id": sid,
                    "symbol": iceberg.symbol,
                    "side": iceberg.side,
                    "size": slice_size,
                    "price": iceberg.price,
                    "order_type": "limit",
                })
            remaining -= slice_size

        self._icebergs[parent_id] = {
            "slice_ids": slices,
            "filled_slices": [],
            "remaining": iceberg.total_size,
            "status": "ACTIVE",
        }
        return {"parent_id": parent_id, "slices": slices, "status": "ACTIVE"}

    def _maybe_advance_iceberg(self, parent_id: str):
        ice = self._icebergs.get(parent_id)
        if not ice:
            return
        for sid in ice["slice_ids"]:
            if sid not in ice["filled_slices"] and sid != ice.get("active_slice"):
                ice["active_slice"] = sid
                if self.on_broker_submit:
                    self.on_broker_submit({"id": sid, "advance": True})
                break
        if ice["remaining"] <= 0:
            ice["status"] = "COMPLETE"

    def get_bracket(self, parent_id: str) -> Optional[dict]:
        return self._brackets.get(parent_id)

    def get_oco(self, parent_id: str) -> Optional[dict]:
        return self._ocos.get(parent_id)

    def get_trailing(self, order_id: str) -> Optional[TrailingStopOrder]:
        return self._trailings.get(order_id)

    def get_iceberg(self, parent_id: str) -> Optional[dict]:
        return self._icebergs.get(parent_id)

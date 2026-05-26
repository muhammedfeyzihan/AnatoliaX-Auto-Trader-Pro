"""
position_lifecycle.py — Partial TP, trailing stop, breakeven, pyramiding.
K215-K218: PositionLifecycleManager.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class LifecycleStage(str, Enum):
    OPEN = "OPEN"
    PARTIAL_TP1 = "PARTIAL_TP1"
    PARTIAL_TP2 = "PARTIAL_TP2"
    PARTIAL_TP3 = "PARTIAL_TP3"
    TRAILING = "TRAILING"
    BREAKEVEN = "BREAKEVEN"
    CLOSED = "CLOSED"


@dataclass
class PositionLifecycleState:
    symbol: str = ""
    side: str = "long"
    size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    stage: LifecycleStage = LifecycleStage.OPEN
    tp_levels: List[Dict] = field(default_factory=list)
    trailing_distance: float = 0.0
    trailing_stop: float = 0.0
    partials_taken: int = 0
    max_partial_levels: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PositionLifecycleManager:
    """
    Pozisyon yasam dongusu yoneticisi.
    Breakeven, kademeli TP, trailing stop, pyramiding.
    """

    def __init__(
        self,
        breakeven_pct: float = 0.05,
        tp1_pct: float = 0.03,
        tp2_pct: float = 0.05,
        tp3_pct: float = 0.08,
        trailing_activation_pct: float = 0.10,
        trailing_step_pct: float = 0.02,
        pyramiding_max: int = 2,
        on_event: Optional[Callable] = None,
    ):
        self.breakeven_pct = breakeven_pct
        self.tp1_pct = tp1_pct
        self.tp2_pct = tp2_pct
        self.tp3_pct = tp3_pct
        self.trailing_activation_pct = trailing_activation_pct
        self.trailing_step_pct = trailing_step_pct
        self.pyramiding_max = pyramiding_max
        self.on_event = on_event
        self._positions: Dict[str, PositionLifecycleState] = {}

    def open_position(self, symbol: str, side: str, size: float, entry_price: float):
        state = PositionLifecycleState(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            current_price=entry_price,
            tp_levels=[
                {"level": 1, "pct": self.tp1_pct, "size_pct": 0.25},
                {"level": 2, "pct": self.tp2_pct, "size_pct": 0.25},
                {"level": 3, "pct": self.tp3_pct, "size_pct": 0.25},
            ],
        )
        self._positions[symbol] = state
        self._emit("OPEN", state)
        return state

    def update_price(self, symbol: str, price: float) -> Optional[Dict]:
        pos = self._positions.get(symbol)
        if not pos:
            return None
        pos.current_price = price
        pos.updated_at = datetime.now(timezone.utc)

        pnl_pct = self._pnl_pct(pos)
        actions = []

        # Breakeven
        if pnl_pct >= self.breakeven_pct and pos.stage == LifecycleStage.OPEN:
            pos.stage = LifecycleStage.BREAKEVEN
            actions.append({"action": "MOVE_SL_BREAKEVEN", "symbol": symbol, "sl": pos.entry_price})
            self._emit("BREAKEVEN", pos)

        # Partial TP levels
        for tp in pos.tp_levels:
            if pnl_pct >= tp["pct"] and pos.partials_taken < tp["level"]:
                pos.partials_taken += 1
                close_size = pos.size * tp["size_pct"]
                pos.size -= close_size
                pos.realized_pnl += close_size * (price - pos.entry_price) * (1 if pos.side == "long" else -1)
                actions.append({"action": f"PARTIAL_TP{tp['level']}", "symbol": symbol, "size": close_size, "price": price})
                stage = getattr(LifecycleStage, f"PARTIAL_TP{tp['level']}")
                pos.stage = stage
                self._emit(f"TP{tp['level']}", pos)

        # Trailing activation
        if pnl_pct >= self.trailing_activation_pct and pos.stage.value.startswith("PARTIAL"):
            pos.stage = LifecycleStage.TRAILING
            pos.trailing_distance = self.trailing_step_pct * pos.entry_price
            pos.trailing_stop = price - pos.trailing_distance if pos.side == "long" else price + pos.trailing_distance
            actions.append({"action": "TRAILING_START", "symbol": symbol, "trailing_stop": pos.trailing_stop})
            self._emit("TRAILING_START", pos)

        # Trailing update
        if pos.stage == LifecycleStage.TRAILING:
            new_stop = self._update_trailing(pos, price)
            if new_stop:
                actions.append({"action": "TRAILING_UPDATE", "symbol": symbol, "trailing_stop": new_stop})

        # Check liquidation / stop
        if pos.size <= 0:
            pos.stage = LifecycleStage.CLOSED
            actions.append({"action": "CLOSE", "symbol": symbol, "price": price})
            self._emit("CLOSE", pos)
            del self._positions[symbol]

        return {"symbol": symbol, "pnl_pct": pnl_pct, "actions": actions, "stage": pos.stage.value}

    def pyramid(self, symbol: str, add_size: float, add_price: float) -> Optional[PositionLifecycleState]:
        pos = self._positions.get(symbol)
        if not pos:
            return None
        if pos.partials_taken >= self.pyramiding_max:
            return pos

        total_size = pos.size + add_size
        pos.entry_price = (pos.entry_price * pos.size + add_price * add_size) / total_size
        pos.size = total_size
        pos.updated_at = datetime.now(timezone.utc)
        self._emit("PYRAMID", pos)
        return pos

    def close_position(self, symbol: str, price: float) -> Optional[PositionLifecycleState]:
        pos = self._positions.get(symbol)
        if not pos:
            return None
        pos.current_price = price
        pos.stage = LifecycleStage.CLOSED
        pos.unrealized_pnl = (price - pos.entry_price) * pos.size * (1 if pos.side == "long" else -1)
        pos.realized_pnl += pos.unrealized_pnl
        self._emit("CLOSE", pos)
        del self._positions[symbol]
        return pos

    def _pnl_pct(self, pos: PositionLifecycleState) -> float:
        if pos.entry_price <= 0:
            return 0.0
        if pos.side == "long":
            return (pos.current_price - pos.entry_price) / pos.entry_price
        return (pos.entry_price - pos.current_price) / pos.entry_price

    def _update_trailing(self, pos: PositionLifecycleState, price: float) -> Optional[float]:
        if pos.side == "long":
            new_stop = price - pos.trailing_distance
            if new_stop > pos.trailing_stop:
                pos.trailing_stop = new_stop
                return new_stop
            if price <= pos.trailing_stop:
                pos.stage = LifecycleStage.CLOSED
                pos.size = 0
        else:
            new_stop = price + pos.trailing_distance
            if new_stop < pos.trailing_stop:
                pos.trailing_stop = new_stop
                return new_stop
            if price >= pos.trailing_stop:
                pos.stage = LifecycleStage.CLOSED
                pos.size = 0
        return None

    def _emit(self, event_type: str, pos: PositionLifecycleState):
        if self.on_event:
            self.on_event(event_type, pos)

    def get_position(self, symbol: str) -> Optional[PositionLifecycleState]:
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, PositionLifecycleState]:
        return self._positions.copy()

    def reset(self):
        self._positions.clear()

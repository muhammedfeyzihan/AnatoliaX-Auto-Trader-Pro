"""
position_manager.py — Lightweight HFT position tracker.
Wraps Account/Position domain objects with HFT-specific logic.
"""

import time
from typing import Dict, Optional
from risk.account import Account
from risk.position import Position


class HFTPositionManager:
    """
    Manages HFT positions: entry, exit, mark-to-market, inventory skew.
    Keeps in-memory state only; persists via Account/Position domain objects.
    """

    def __init__(self, account: Account):
        self.account = account
        self._entry_times: Dict[str, float] = {}
        self._exit_prices: Dict[str, float] = {}

    def enter_position(self, symbol: str, qty: float, price: float, commission: float = 0.0) -> bool:
        """Enter a new long position."""
        ok = self.account.open_position(symbol, qty, price, commission)
        if ok:
            self._entry_times[symbol] = time.time()
        return ok

    def exit_position(self, symbol: str, qty: float, price: float, commission: float = 0.0) -> Optional[float]:
        """Close position (or part of it). Returns realized P&L."""
        pnl = self.account.close_position(symbol, qty, price, commission)
        if pnl is not None:
            self._exit_prices[symbol] = price
            self._entry_times.pop(symbol, None)
        return pnl

    def mark_all(self, prices: Dict[str, float]):
        """Mark all open positions to current market prices."""
        self.account.mark_to_market(prices)

    def get_inventory_skew(self) -> float:
        """
        Return inventory skew: -1 (all short) to +1 (all long).
        For BIST spot, always long-only, so this measures concentration.
        """
        total_mv = sum(p.market_value for p in self.account.positions.values() if p.is_open)
        if total_mv <= 0:
            return 0.0
        # Concentration: max position / total
        max_mv = max((p.market_value for p in self.account.positions.values() if p.is_open), default=0.0)
        return max_mv / total_mv if total_mv > 0 else 0.0

    def holding_time_seconds(self, symbol: str) -> float:
        """Return how long position has been held."""
        entry = self._entry_times.get(symbol)
        if entry is None:
            return 0.0
        return time.time() - entry

    def can_exit(self, symbol: str, current_price: float, sl_pct: float, tp_pct: float) -> tuple[bool, str]:
        """Check if position should be exited based on SL/TP."""
        pos = self.account.get_position(symbol)
        if pos is None or not pos.is_open:
            return False, "No open position"

        entry = pos.avg_entry_price
        if entry <= 0:
            return False, "Invalid entry price"

        sl_price = entry * (1 - sl_pct)
        tp_price = entry * (1 + tp_pct)

        if current_price <= sl_price:
            return True, "SL"
        if current_price >= tp_price:
            return True, "TP"

        # Max hold time: 120 seconds for M1
        if self.holding_time_seconds(symbol) > 120:
            return True, "TIME"

        return False, "HOLD"

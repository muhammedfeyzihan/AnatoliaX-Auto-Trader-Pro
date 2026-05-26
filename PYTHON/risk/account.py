"""
account.py — Account domain object.
Inspired by Nautilus Trader's CashAccount / MarginAccount.

Tracks cash balance, equity, realized P&L, and margin usage.
Designed for in-memory fast accounting; persists via SQLAlchemy separately if needed.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from risk.position import Position


@dataclass
class Account:
    """
    In-memory cash-accounting tracker.
    BIST spot piyasasi icin margin gereksinimi yoktur; bu model cash accounting icindir.
    """

    account_id: str = "default"
    base_currency: str = "TRY"
    initial_cash: float = 100_000.0
    cash: float = field(default=0.0)
    realized_pnl: float = 0.0
    total_commission: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)

    # Limits
    max_position_value_pct: float = 0.02  # Max % of equity per position
    max_total_positions: int = 5

    def __post_init__(self):
        if self.cash == 0.0 and self.initial_cash != 0.0:
            self.cash = self.initial_cash

    def can_open_position(self, symbol: str, qty: float, price: float) -> tuple[bool, str]:
        """Check if a new position can be opened. Returns (allowed, reason)."""
        notional = qty * price

        if notional > self.equity * self.max_position_value_pct:
            return False, f"Position size {notional:.2f} exceeds {self.max_position_value_pct*100}% of equity"

        open_count = sum(1 for p in self.positions.values() if p.is_open)
        if open_count >= self.max_total_positions:
            return False, f"Max positions ({self.max_total_positions}) reached"

        if notional > self.cash:
            return False, f"Insufficient cash: need {notional:.2f}, have {self.cash:.2f}"

        return True, "OK"

    def open_position(
        self,
        symbol: str,
        qty: float,
        price: float,
        commission: float = 0.0,
    ) -> bool:
        """Open a new LONG position (deduct cash, create position)."""
        allowed, reason = self.can_open_position(symbol, qty, price)
        if not allowed:
            return False

        notional = qty * price
        self.cash -= notional
        self.total_commission += commission

        pos = self.positions.get(symbol)
        if pos is None:
            pos = Position(symbol=symbol)
            self.positions[symbol] = pos

        pos.apply_fill(qty, price, "BUY", commission)
        return True

    def close_position(
        self,
        symbol: str,
        qty: float,
        price: float,
        commission: float = 0.0,
    ) -> Optional[float]:
        """
        Close a position (or part of it). Returns realized P&L from this close, or None.
        Cash is credited with sale proceeds.
        """
        pos = self.positions.get(symbol)
        if pos is None or not pos.is_open:
            return None

        pre_realized = pos.realized_pnl
        pos.apply_fill(qty, price, "SELL", commission)
        realized_from_this = pos.realized_pnl - pre_realized

        proceeds = qty * price
        self.cash += proceeds
        self.total_commission += commission
        self.realized_pnl += realized_from_this

        if not pos.is_open:
            # Fully closed; keep the Position object for history.
            # Cash already credited above; no further action needed.
            pass

        return realized_from_this

    def mark_to_market(self, prices: Dict[str, float]) -> None:
        """Update unrealized P&L for all open positions using current market prices."""
        for symbol, pos in self.positions.items():
            if pos.is_open and symbol in prices:
                pos.mark_price(prices[symbol])

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def equity(self) -> float:
        """Total equity = cash + unrealized P&L."""
        return self.cash + self.unrealized_pnl

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_return_pct(self) -> float:
        if self.initial_cash <= 0:
            return 0.0
        return (self.equity - self.initial_cash) / self.initial_cash

    @property
    def open_position_count(self) -> int:
        return sum(1 for p in self.positions.values() if p.is_open)

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "base_currency": self.base_currency,
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "equity": self.equity,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_commission": self.total_commission,
            "total_return_pct": self.total_return_pct,
            "open_positions": self.open_position_count,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
        }

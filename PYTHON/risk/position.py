"""
position.py — Position domain object.
Inspired by Nautilus Trader's Position model.

Tracks average entry price, quantity, realized/unrealized P&L
for a single symbol position. Supports both long and short sides.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Position:
    """
    In-memory position tracker for a single symbol.
    Does NOT persist to DB — use alongside SQLAlchemy models if needed.
    """

    symbol: str = ""
    side: Literal["LONG", "SHORT", "FLAT"] = "FLAT"
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_commission: float = 0.0
    trade_count: int = 0

    def apply_fill(
        self,
        fill_qty: float,
        fill_price: float,
        fill_side: Literal["BUY", "SELL"],
        commission: float = 0.0,
    ) -> None:
        """
        Process a fill event and update position state.
        BUY fills increase long quantity; SELL fills decrease long (or increase short).
        """
        if fill_qty <= 0:
            return

        self.total_commission += commission
        self.trade_count += 1

        is_buy = fill_side.upper() == "BUY"
        qty = fill_qty

        if self.side == "FLAT":
            self.side = "LONG" if is_buy else "SHORT"
            self.quantity = qty
            self.avg_entry_price = fill_price
        elif self.side == "LONG":
            if is_buy:
                # Add to long
                total_cost = (self.quantity * self.avg_entry_price) + (qty * fill_price)
                self.quantity += qty
                self.avg_entry_price = total_cost / self.quantity if self.quantity > 0 else 0.0
            else:
                # Reduce / close long
                if qty >= self.quantity:
                    # Full close
                    self.realized_pnl += (fill_price - self.avg_entry_price) * self.quantity - commission
                    self.quantity = 0.0
                    self.side = "FLAT"
                    self.avg_entry_price = 0.0
                else:
                    # Partial close
                    self.realized_pnl += (fill_price - self.avg_entry_price) * qty - commission
                    self.quantity -= qty
        elif self.side == "SHORT":
            if not is_buy:
                # Add to short
                total_cost = (self.quantity * self.avg_entry_price) + (qty * fill_price)
                self.quantity += qty
                self.avg_entry_price = total_cost / self.quantity if self.quantity > 0 else 0.0
            else:
                # Reduce / close short
                if qty >= self.quantity:
                    self.realized_pnl += (self.avg_entry_price - fill_price) * self.quantity - commission
                    self.quantity = 0.0
                    self.side = "FLAT"
                    self.avg_entry_price = 0.0
                else:
                    self.realized_pnl += (self.avg_entry_price - fill_price) * qty - commission
                    self.quantity -= qty

    def mark_price(self, current_price: float) -> None:
        """Update unrealized P&L based on current market price."""
        if self.side == "FLAT" or self.quantity <= 0:
            self.unrealized_pnl = 0.0
            return

        if self.side == "LONG":
            self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.avg_entry_price - current_price) * self.quantity

    @property
    def market_value(self) -> float:
        """Approximate market value of the position (quantity * avg_entry)."""
        return self.quantity * self.avg_entry_price

    @property
    def is_open(self) -> bool:
        return self.side != "FLAT" and self.quantity > 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "avg_entry_price": self.avg_entry_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_commission": self.total_commission,
            "trade_count": self.trade_count,
            "market_value": self.market_value,
        }

"""
instrument.py — Standardized BIST instrument definitions.
Inspired by Nautilus Trader's Instrument model.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Instrument:
    """
    Standardized instrument definition for any exchange.
    For BIST: lot_size=1, tick_size=0.01 typically.
    """
    symbol: str = ""
    name: str = ""
    exchange: str = "BIST"
    currency: str = "TRY"
    tick_size: float = 0.01
    lot_size: float = 1.0
    sector: str = ""
    sub_sector: str = ""
    is_index: bool = False
    # BIST-specific
    bist30: bool = False
    bist50: bool = False
    bist100: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format_price(self, price: float) -> float:
        """Round price to tick size."""
        if self.tick_size <= 0:
            return price
        ticks = round(price / self.tick_size)
        return round(ticks * self.tick_size, 10)

    def validate_lot(self, quantity: float) -> tuple[bool, float]:
        """Check if quantity is a valid multiple of lot_size."""
        if self.lot_size <= 0:
            return True, quantity
        multiple = round(quantity / self.lot_size) * self.lot_size
        is_valid = abs(quantity - multiple) < 1e-9
        return is_valid, multiple

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "currency": self.currency,
            "tick_size": self.tick_size,
            "lot_size": self.lot_size,
            "sector": self.sector,
            "bist30": self.bist30,
            "bist50": self.bist50,
            "bist100": self.bist100,
        }

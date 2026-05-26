"""
order_types.py — Advanced order types for AnatoliaX.
Inspired by Nautilus Trader's OrderType and contingency order model.
BIST brokers typically only support MARKET/LIMIT natively;
advanced types are emulated locally by the ContingencyManager.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class OrderType(str, Enum):
    """Supported order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP_MARKET = "trailing_stop_market"
    TRAILING_STOP_LIMIT = "trailing_stop_limit"
    BRACKET = "bracket"
    OCO = "oco"
    ICEBERG = "iceberg"


class TimeInForce(str, Enum):
    """Time-in-force modes."""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


@dataclass
class BracketOrder:
    """
    Entry + TP + SL as a unit.
    BIST brokers don't support this natively; we emulate it locally.
    """
    symbol: str = ""
    side: str = "BUY"
    size: float = 0.0
    entry_price: float = 0.0
    entry_type: OrderType = OrderType.LIMIT
    sl_price: float = 0.0
    tp_price: float = 0.0
    trailing_distance: Optional[float] = None  # If set, trailing stop instead of fixed SL
    time_in_force: TimeInForce = TimeInForce.GTC
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCOOrder:
    """
    One-Cancels-Other: two child orders (e.g. TP + SL).
    When one fills, the other is cancelled automatically.
    """
    symbol: str = ""
    side: str = "SELL"  # Typically exit side
    size: float = 0.0
    limit_price: Optional[float] = None   # TP leg
    stop_price: Optional[float] = None    # SL leg
    time_in_force: TimeInForce = TimeInForce.GTC
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrailingStopOrder:
    """
    Trailing stop that follows price at a fixed distance/percentage.
    Locally emulated by updating the stop price as market moves favorably.
    """
    symbol: str = ""
    side: str = "SELL"
    size: float = 0.0
    distance: float = 0.0        # Absolute price distance
    distance_pct: Optional[float] = None   # Percentage distance (alternative)
    current_stop: float = 0.0
    activation_price: Optional[float] = None  # Trail only after this price
    time_in_force: TimeInForce = TimeInForce.GTC
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_stop(self, current_market_price: float, is_long: bool = True):
        """Update trailing stop based on new market price."""
        if self.distance_pct:
            actual_distance = current_market_price * (self.distance_pct / 100)
        else:
            actual_distance = self.distance

        if is_long:
            new_stop = current_market_price - actual_distance
            if new_stop > self.current_stop:
                self.current_stop = new_stop
        else:
            new_stop = current_market_price + actual_distance
            if new_stop < self.current_stop:
                self.current_stop = new_stop

        # Activation check
        if self.activation_price:
            if is_long and current_market_price < self.activation_price:
                return
            if not is_long and current_market_price > self.activation_price:
                return


@dataclass
class IcebergOrder:
    """
    Large order split into smaller visible chunks.
    Only 'display_qty' shown at a time; remainder hidden.
    """
    symbol: str = ""
    side: str = "BUY"
    total_size: float = 0.0
    display_qty: float = 0.0
    price: float = 0.0
    time_in_force: TimeInForce = TimeInForce.DAY
    metadata: Dict[str, Any] = field(default_factory=dict)

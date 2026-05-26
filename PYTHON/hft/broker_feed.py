"""
broker_feed.py — Broker data feed adapter for HFT.
Abstracts WebSocket/REST tick feeds from broker APIs.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timezone


class BrokerFeed(ABC):
    """Abstract broker data feed."""

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def subscribe_ticks(self, symbols: list[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass


class SimulatedBrokerFeed(BrokerFeed):
    """
    Simulated broker feed for backtesting.
    Replays tick DataFrame as individual ticks.
    """

    def __init__(self, tick_df: "pd.DataFrame"):
        self.tick_df = tick_df
        self._connected = False
        self._callback: Optional[Callable] = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def subscribe_ticks(self, symbols: list[str], callback: Callable) -> None:
        self._callback = callback

    def replay(self, speed: float = 1.0):
        """Replay all ticks through callback."""
        import time
        for _, row in self.tick_df.iterrows():
            tick = {
                "symbol": row.get("symbol", "UNKNOWN"),
                "timestamp": row.get("timestamp", datetime.now(timezone.utc)),
                "price": row["price"],
                "size": row.get("size", 0.0),
                "bid": row.get("bid"),
                "ask": row.get("ask"),
            }
            if self._callback:
                self._callback(tick)
            if speed > 0:
                time.sleep(0.001 / speed)

    @property
    def is_connected(self) -> bool:
        return self._connected

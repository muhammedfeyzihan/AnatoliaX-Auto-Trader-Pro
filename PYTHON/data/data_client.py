"""
data_client.py — Abstract DataClient / ExecutionClient pattern.
Inspired by Nautilus Trader's modular adapter architecture.

Allows existing fetchers (YahooFetcher, TradingViewScraper, etc.) to be adapted
to a common interface, enabling plug-and-play data sources.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import pandas as pd


class DataClient(ABC):
    """
    Abstract base class for all market data clients.
    Provides a unified interface for bar and tick data retrieval.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data source."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if client is currently connected."""
        pass

    @abstractmethod
    def request_bars(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Request historical bar (OHLCV) data."""
        pass

    @abstractmethod
    def request_ticks(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Request historical tick data."""
        pass

    @abstractmethod
    def subscribe_bars(
        self,
        symbol: str,
        interval: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Subscribe to live bar updates."""
        pass

    @abstractmethod
    def subscribe_ticks(
        self,
        symbol: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Subscribe to live tick updates."""
        pass

    @abstractmethod
    def unsubscribe_all(self) -> None:
        """Cancel all active subscriptions."""
        pass

    @property
    @abstractmethod
    def venue(self) -> str:
        """Return the venue/exchange name this client serves (e.g. 'BIST')."""
        pass


class ExecutionClient(ABC):
    """
    Abstract base class for execution/broker clients.
    Separates data from execution concerns.
    """

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an order. Returns execution report dict."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    def get_positions(self) -> list:
        pass

    @abstractmethod
    def get_account(self) -> dict:
        pass

    @property
    @abstractmethod
    def venue(self) -> str:
        pass


class YahooDataClient(DataClient):
    """
    Adapter: wraps existing YahooFetcher into the DataClient ABC.
    """

    def __init__(self, cache_ttl: int = 3600):
        from data.yahoo_fetcher import YahooFetcher
        self._fetcher = YahooFetcher(cache_ttl=cache_ttl)
        self._connected = False
        self._subscriptions: Dict[str, Any] = {}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._subscriptions.clear()

    def is_connected(self) -> bool:
        return self._connected

    def request_bars(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        if not self._connected:
            raise RuntimeError("Client not connected. Call connect() first.")

        # Yahoo period mapping; ignore start/end for now — use period heuristic
        period = "6mo"
        if start and end:
            delta = (end - start).days
            if delta <= 7:
                period = "1mo"
            elif delta <= 30:
                period = "3mo"
            elif delta <= 180:
                period = "6mo"
            else:
                period = "1y"

        df = self._fetcher.fetch(symbol, period=period, interval=interval, use_cache=True)

        if start and "timestamp" in df.columns:
            df = df[df["timestamp"] >= start]
        if end and "timestamp" in df.columns:
            df = df[df["timestamp"] <= end]

        return df

    def request_ticks(self, symbol: str, start=None, end=None) -> pd.DataFrame:
        # Yahoo Finance does not provide tick-level data
        return pd.DataFrame()

    def subscribe_bars(self, symbol: str, interval: str, callback) -> None:
        # Polling-based simulation for Yahoo
        self._subscriptions[f"{symbol}_{interval}"] = (symbol, interval, callback)

    def subscribe_ticks(self, symbol: str, callback) -> None:
        raise NotImplementedError("Yahoo Finance does not support live tick streams")

    def unsubscribe_all(self) -> None:
        self._subscriptions.clear()

    @property
    def venue(self) -> str:
        return "YAHOO"


class FeedAggregatorDataClient(DataClient):
    """
    Adapter: wraps FeedAggregator into the DataClient ABC.
    This is the preferred client for BIST because it uses fallback chain.
    """

    def __init__(self, cache_ttl: int = 3600):
        from data.feed_aggregator import FeedAggregator
        self._agg = FeedAggregator(cache_ttl=cache_ttl)
        self._connected = False
        self._subscriptions: Dict[str, Any] = {}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._subscriptions.clear()

    def is_connected(self) -> bool:
        return self._connected

    def request_bars(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        if not self._connected:
            raise RuntimeError("Client not connected. Call connect() first.")

        df = self._agg.fetch(symbol, interval=interval, period="6mo")

        if start and "timestamp" in df.columns:
            df = df[df["timestamp"] >= start]
        if end and "timestamp" in df.columns:
            df = df[df["timestamp"] <= end]

        return df

    def request_ticks(self, symbol: str, start=None, end=None) -> pd.DataFrame:
        # Aggregator does not provide tick data currently
        return pd.DataFrame()

    def subscribe_bars(self, symbol: str, interval: str, callback) -> None:
        self._subscriptions[f"{symbol}_{interval}"] = (symbol, interval, callback)

    def subscribe_ticks(self, symbol: str, callback) -> None:
        raise NotImplementedError("FeedAggregator does not support live tick streams")

    def unsubscribe_all(self) -> None:
        self._subscriptions.clear()

    @property
    def venue(self) -> str:
        return "BIST_AGGREGATOR"

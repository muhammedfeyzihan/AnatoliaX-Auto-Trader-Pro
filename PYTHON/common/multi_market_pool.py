"""
multi_market_pool.py — Simultaneous Multi-Market Monitoring Pool

Supports 20–50 concurrent markets with async event-driven updates.
Integrates with AsyncEventBus, FeedAggregator, and Redis/NATS pubsub.

Usage:
    from common.multi_market_pool import MultiMarketPool
    pool = MultiMarketPool(max_markets=50)
    pool.subscribe(["THYAO", "GARAN", "BTCUSDT", "EURUSD"])
    pool.start_monitoring(interval_seconds=5)
    snapshot = pool.get_snapshot("THYAO")
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np
import pandas as pd

from common.async_event_bus import AsyncEventBus


@dataclass
class MarketSnapshot:
    symbol: str
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    change_pct: float = 0.0
    atr_pct: float = 0.0
    spread_pct: float = 0.0
    timestamp: float = field(default_factory=time.time)
    stale: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "change_pct": self.change_pct,
            "atr_pct": self.atr_pct,
            "spread_pct": self.spread_pct,
            "timestamp": self.timestamp,
            "stale": self.stale,
        }


class MultiMarketPool:
    """
    Async multi-market monitor supporting up to 50 symbols.
    Uses AsyncEventBus for internal pub/sub.
    Optional Redis/NATS bridge for distributed setups.
    """

    def __init__(
        self,
        max_markets: int = 50,
        stale_seconds: float = 30.0,
        use_redis: bool = False,
        use_nats: bool = False,
    ):
        self.max_markets = max(1, max_markets)
        self.stale_seconds = stale_seconds
        self._symbols: set[str] = set()
        self._snapshots: Dict[str, MarketSnapshot] = {}
        self._history: Dict[str, List[MarketSnapshot]] = defaultdict(list)
        self._max_history = 1000
        self._running = False
        self._bus = AsyncEventBus()
        self._listeners: List[Callable] = []

        # Optional distributed bus
        self._redis = None
        self._nats = None
        if use_redis:
            self._redis = self._init_redis()
        if use_nats:
            self._nats = self._init_nats()

    def _init_redis(self):
        try:
            import redis
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            return redis.Redis(host=host, port=port, decode_responses=True)
        except Exception:
            return None

    def _init_nats(self):
        try:
            import nats
            return nats  # stub, real connection async
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------
    def subscribe(self, symbols: List[str]) -> List[str]:
        """Add symbols to monitoring pool. Returns actually added."""
        added = []
        for s in symbols:
            sym = s.upper()
            if len(self._symbols) >= self.max_markets:
                break
            if sym not in self._symbols:
                self._symbols.add(sym)
                self._snapshots[sym] = MarketSnapshot(symbol=sym)
                added.append(sym)
        return added

    def unsubscribe(self, symbols: List[str]):
        for s in symbols:
            sym = s.upper()
            self._symbols.discard(sym)
            self._snapshots.pop(sym, None)
            self._history.pop(sym, None)

    def list_symbols(self) -> List[str]:
        return sorted(self._symbols)

    # ------------------------------------------------------------------
    # Snapshot updates
    # ------------------------------------------------------------------
    def update(self, symbol: str, price: float, bid: float = 0.0, ask: float = 0.0,
               volume: float = 0.0, change_pct: float = 0.0, atr_pct: float = 0.0):
        """Push a tick update into the pool."""
        sym = symbol.upper()
        if sym not in self._symbols:
            return
        spread_pct = ((ask - bid) / ((ask + bid) / 2.0) * 100.0) if bid > 0 and ask > 0 else 0.0
        snap = MarketSnapshot(
            symbol=sym,
            price=price,
            bid=bid,
            ask=ask,
            volume=volume,
            change_pct=change_pct,
            atr_pct=atr_pct,
            spread_pct=round(spread_pct, 4),
            timestamp=time.time(),
            stale=False,
        )
        self._snapshots[sym] = snap
        self._history[sym].append(snap)
        if len(self._history[sym]) > self._max_history:
            self._history[sym] = self._history[sym][-self._max_history:]

        # Emit event (safely, even if no event loop running)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._bus.publish("market.tick", {"symbol": sym, "snapshot": snap.to_dict()}))
        except RuntimeError:
            pass

        # Distributed publish
        if self._redis:
            try:
                self._redis.publish(f"anatoliax:tick:{sym}", str(snap.to_dict()))
            except Exception:
                pass

    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        snap = self._snapshots.get(symbol.upper())
        if snap is None:
            return None
        # Stale check
        if time.time() - snap.timestamp > self.stale_seconds:
            snap.stale = True
        return snap

    def get_all_snapshots(self) -> Dict[str, MarketSnapshot]:
        now = time.time()
        out = {}
        for sym, snap in self._snapshots.items():
            if now - snap.timestamp > self.stale_seconds:
                snap.stale = True
            out[sym] = snap
        return out

    def get_history(self, symbol: str, last_n: int = 100) -> List[MarketSnapshot]:
        return self._history.get(symbol.upper(), [])[-last_n:]

    # ------------------------------------------------------------------
    # Async monitoring loop
    # ------------------------------------------------------------------
    async def _monitor_loop(self, interval_seconds: float, fetcher: Optional[Callable] = None):
        """Background loop that fetches data for all symbols."""
        while self._running:
            if fetcher:
                for sym in list(self._symbols):
                    try:
                        data = fetcher(sym)
                        if data:
                            self.update(sym, **data)
                    except Exception:
                        pass
            else:
                # No fetcher = external pushes only; just emit heartbeat
                await self._bus.publish("market.heartbeat", {"time": time.time(), "symbols": len(self._symbols)})
            await asyncio.sleep(interval_seconds)

    def start_monitoring(self, interval_seconds: float = 5.0, fetcher: Optional[Callable] = None):
        """Start async monitoring in background."""
        self._running = True
        asyncio.create_task(self._monitor_loop(interval_seconds, fetcher))

    def stop_monitoring(self):
        self._running = False

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def get_volatility_ranking(self) -> List[tuple[str, float]]:
        """Return symbols sorted by ATR% descending."""
        items = [(sym, snap.atr_pct) for sym, snap in self._snapshots.items() if snap.atr_pct > 0]
        return sorted(items, key=lambda x: x[1], reverse=True)

    def get_spread_ranking(self) -> List[tuple[str, float]]:
        """Return symbols sorted by spread% descending."""
        items = [(sym, snap.spread_pct) for sym, snap in self._snapshots.items() if snap.spread_pct > 0]
        return sorted(items, key=lambda x: x[1], reverse=True)

    def get_stale_symbols(self) -> List[str]:
        now = time.time()
        return [sym for sym, snap in self._snapshots.items() if now - snap.timestamp > self.stale_seconds]

    def to_dataframe(self) -> pd.DataFrame:
        """Export current snapshots as DataFrame."""
        rows = [s.to_dict() for s in self._snapshots.values()]
        return pd.DataFrame(rows)


if __name__ == "__main__":
    pool = MultiMarketPool(max_markets=50)
    pool.subscribe(["THYAO", "GARAN", "BTCUSDT", "EURUSD"])
    pool.update("THYAO", price=103.0, bid=102.9, ask=103.1, volume=50000, change_pct=1.2, atr_pct=0.8)
    print(pool.get_snapshot("THYAO"))
    print(pool.to_dataframe())

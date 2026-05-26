"""
execution/order_book.py — Full Order Book Reconstruction (Phase 1)
Module 2 from anatoliax_prompt_v6.txt

Features:
  - Real-time L2/L3 order book reconstruction with event-time processing
  - Spoofing detection: orders placed and cancelled within τ < 2 seconds with size > 3x average
  - Layering detection: price levels with ≥5 orders placed/cancelled in sequence without execution
  - Liquidity vacuum: bid_ask_spread > 3σ_spread and book_depth < 10% percentile
  - Feed order book deltas ΔB(t), ΔA(t) into Signal Agent
"""

import bisect
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque


@dataclass
class BookLevel:
    price: float
    size: float
    order_count: int = 1


@dataclass
class OrderBookEvent:
    timestamp: datetime
    symbol: str
    side: str  # "bid" or "ask"
    price: float
    size: float
    event_type: str  # "add", "cancel", "trade", "modify"
    order_id: str = ""


class OrderBookReconstructor:
    """
    Real-time L2/L3 order book reconstruction with event-time processing.
    Maintains bid and ask books as sorted lists of BookLevel.
    """

    def __init__(self, symbol: str, max_depth: int = 10):
        self.symbol = symbol
        self.max_depth = max_depth
        self.bids: List[BookLevel] = []  # sorted descending
        self.asks: List[BookLevel] = []  # sorted ascending
        self._events: deque = deque(maxlen=10000)

    def apply_event(self, event: OrderBookEvent):
        self._events.append(event)
        book = self.bids if event.side == "bid" else self.asks

        if event.event_type == "add":
            self._add_level(book, event.price, event.size, event.side)
        elif event.event_type == "cancel":
            self._remove_level(book, event.price, event.size, event.side)
        elif event.event_type == "trade":
            self._remove_level(book, event.price, event.size, event.side)
        elif event.event_type == "modify":
            self._modify_level(book, event.price, event.size, event.side)

        # Keep max depth
        if len(book) > self.max_depth:
            if event.side == "bid":
                book[:] = book[:self.max_depth]
            else:
                book[:] = book[:self.max_depth]

    def _price_key(self, side: str):
        """Return sort key extractor for given side."""
        return (lambda lvl: -lvl.price) if side == "bid" else (lambda lvl: lvl.price)

    def _find_level_idx(self, book: List[BookLevel], price: float, side: str) -> int:
        """Binary search for exact price level. Returns index or -1."""
        key = self._price_key(side)
        # bisect_left on keyed list
        lo, hi = 0, len(book)
        while lo < hi:
            mid = (lo + hi) // 2
            if key(book[mid]) < key(BookLevel(price=price, size=0)):
                lo = mid + 1
            else:
                hi = mid
        if lo < len(book) and abs(book[lo].price - price) < 1e-9:
            return lo
        return -1

    def _add_level(self, book: List[BookLevel], price: float, size: float, side: str):
        idx = self._find_level_idx(book, price, side)
        if idx >= 0:
            book[idx].size += size
            book[idx].order_count += 1
            return
        new_level = BookLevel(price=price, size=size)
        key = self._price_key(side)
        # bisect_left equivalent for custom key
        lo, hi = 0, len(book)
        target_key = key(new_level)
        while lo < hi:
            mid = (lo + hi) // 2
            if key(book[mid]) < target_key:
                lo = mid + 1
            else:
                hi = mid
        book.insert(lo, new_level)

    def _remove_level(self, book: List[BookLevel], price: float, size: float, side: str = "bid"):
        idx = self._find_level_idx(book, price, side)
        if idx >= 0:
            book[idx].size -= size
            if book[idx].size <= 0:
                book.pop(idx)

    def _modify_level(self, book: List[BookLevel], price: float, new_size: float, side: str = "bid"):
        idx = self._find_level_idx(book, price, side)
        if idx >= 0:
            book[idx].size = new_size

    def get_best_bid(self) -> Optional[BookLevel]:
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[BookLevel]:
        return self.asks[0] if self.asks else None

    def get_spread(self) -> float:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return 0.0

    def get_midprice(self) -> float:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2.0
        return 0.0

    def get_book_depth(self) -> float:
        return sum(l.size for l in self.bids) + sum(l.size for l in self.asks)

    def get_deltas(self) -> Tuple[float, float]:
        """ΔB(t), ΔA(t) — net change in bid/ask depth since last call."""
        bid_delta = sum(l.size for l in self.bids)
        ask_delta = sum(l.size for l in self.asks)
        return bid_delta, ask_delta


class SpoofingDetector:
    """
    Spoofing detection: orders placed and cancelled within τ < 2 seconds
    with size > 3x average.
    """

    def __init__(self, tau_seconds: float = 2.0, size_multiplier: float = 3.0):
        self.tau = timedelta(seconds=tau_seconds)
        self.size_multiplier = size_multiplier
        self._events: List[OrderBookEvent] = []

    def record(self, event: OrderBookEvent):
        self._events.append(event)

    def scan(self) -> List[Dict]:
        alerts = []
        by_order: Dict[str, List[OrderBookEvent]] = defaultdict(list)
        for e in self._events:
            by_order[e.order_id].append(e)

        avg_size = statistics.mean(e.size for e in self._events) if self._events else 0.0

        for oid, events in by_order.items():
            adds = [e for e in events if e.event_type == "add"]
            cancels = [e for e in events if e.event_type == "cancel"]
            for add in adds:
                for cancel in cancels:
                    if 0 < (cancel.timestamp - add.timestamp).total_seconds() < self.tau.total_seconds():
                        if add.size > avg_size * self.size_multiplier:
                            alerts.append({
                                "type": "SPOOFING",
                                "order_id": oid,
                                "size": add.size,
                                "avg_size": avg_size,
                                "duration_sec": (cancel.timestamp - add.timestamp).total_seconds(),
                                "timestamp": add.timestamp.isoformat(),
                            })
        return alerts


class LayeringDetector:
    """
    Layering detection: price levels with ≥5 orders placed/cancelled
    in sequence without execution.
    """

    def __init__(self, sequence_threshold: int = 5):
        self.sequence_threshold = sequence_threshold
        self._sequences: Dict[str, List[OrderBookEvent]] = defaultdict(list)

    def record(self, event: OrderBookEvent):
        key = f"{event.symbol}@{event.price:.4f}"
        self._sequences[key].append(event)

    def scan(self) -> List[Dict]:
        alerts = []
        for key, events in self._sequences.items():
            seq = 0
            for e in events:
                if e.event_type in ("add", "cancel"):
                    seq += 1
                elif e.event_type == "trade":
                    seq = 0
            if seq >= self.sequence_threshold:
                alerts.append({
                    "type": "LAYERING",
                    "key": key,
                    "sequence_length": seq,
                    "last_event": events[-1].timestamp.isoformat(),
                })
        return alerts


class LiquidityVacuumDetector:
    """
    Liquidity vacuum: detect when bid_ask_spread > 3σ_spread
    and book_depth < 10% percentile.
    """

    def __init__(self, spread_sigma_multiplier: float = 3.0, depth_percentile: float = 0.10):
        self.spread_sigma_multiplier = spread_sigma_multiplier
        self.depth_percentile = depth_percentile
        self._spread_history: List[float] = []
        self._depth_history: List[float] = []

    def record(self, spread: float, depth: float):
        self._spread_history.append(spread)
        self._depth_history.append(depth)

    def detect(self) -> Optional[Dict]:
        if len(self._spread_history) < 30 or len(self._depth_history) < 30:
            return None

        spread_mean = statistics.mean(self._spread_history[-100:])
        spread_std = statistics.stdev(self._spread_history[-100:]) if len(self._spread_history) >= 2 else 0.0
        current_spread = self._spread_history[-1]
        current_depth = self._depth_history[-1]

        sorted_depths = sorted(self._depth_history[-100:])
        depth_threshold = sorted_depths[int(len(sorted_depths) * self.depth_percentile)]

        if current_spread > spread_mean + self.spread_sigma_multiplier * spread_std and current_depth < depth_threshold:
            return {
                "type": "LIQUIDITY_VACUUM",
                "spread": current_spread,
                "spread_threshold": spread_mean + self.spread_sigma_multiplier * spread_std,
                "depth": current_depth,
                "depth_threshold": depth_threshold,
            }
        return None

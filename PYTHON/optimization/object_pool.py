"""
optimization/object_pool.py — Object Pool for High-Frequency Event Allocation

Eliminates GC pressure in hot paths by pre-allocating and reusing objects.
Inspired by crypto-lob (C++) memory pools and latencyarb zero-allocation design.
"""

from collections import deque
from typing import TypeVar, Type, Optional, Dict, Any
import time


T = TypeVar("T")


class ObjectPool:
    """
    Generic fixed-size object pool.
    Falls back to allocation if pool exhausted (no blocking).
    """

    def __init__(self, factory: callable, capacity: int = 10_000):
        self._factory = factory
        self._capacity = capacity
        self._available: deque = deque(maxlen=capacity)
        self._total_created = 0
        self._total_reused = 0
        self._total_returned = 0
        self._prefill()

    def _prefill(self):
        while len(self._available) < self._capacity:
            self._available.append(self._factory())
            self._total_created += 1

    def acquire(self) -> Any:
        if self._available:
            self._total_reused += 1
            return self._available.pop()
        self._total_created += 1
        return self._factory()

    def release(self, obj: Any, reset_fn: Optional[callable] = None):
        if reset_fn:
            reset_fn(obj)
        if len(self._available) < self._capacity:
            self._available.append(obj)
            self._total_returned += 1

    def stats(self) -> Dict[str, Any]:
        return {
            "capacity": self._capacity,
            "available": len(self._available),
            "total_created": self._total_created,
            "total_reused": self._total_reused,
            "total_returned": self._total_returned,
            "reuse_rate_pct": (self._total_reused / max(self._total_created, 1)) * 100,
        }


class DataclassPool(ObjectPool):
    """
    Specialized pool for dataclasses. Uses __dict__ reset for fast return.
    """

    def __init__(self, cls: Type[T], capacity: int = 10_000, default_kwargs: Optional[Dict] = None):
        self._cls = cls
        self._default_kwargs = default_kwargs or {}
        super().__init__(factory=lambda: cls(**self._default_kwargs), capacity=capacity)

    def release(self, obj: T):
        # Fast reset: clear any mutated fields back to defaults
        for k, v in self._default_kwargs.items():
            setattr(obj, k, v)
        super().release(obj)


# ---------------------------------------------------------------------------
# Pre-built pools for AnatoliaX hot-path objects
# ---------------------------------------------------------------------------
from common.event_sourcing import Event, EventType
from execution.order_book import OrderBookEvent, BookLevel


def _event_factory():
    return Event(event_type=EventType.MARKET_DATA, payload={}, timestamp=0)


def _order_book_event_factory():
    return OrderBookEvent(
        timestamp=None, symbol="", side="bid", price=0.0, size=0.0,
        event_type="add", order_id=""
    )


# Module-level singletons (lazy init on first import)
_EVENT_POOL: Optional[ObjectPool] = None
_ORDER_BOOK_EVENT_POOL: Optional[ObjectPool] = None
_BOOK_LEVEL_POOL: Optional[ObjectPool] = None


def get_event_pool(capacity: int = 10_000) -> ObjectPool:
    global _EVENT_POOL
    if _EVENT_POOL is None:
        _EVENT_POOL = ObjectPool(_event_factory, capacity)
    return _EVENT_POOL


def get_order_book_event_pool(capacity: int = 10_000) -> ObjectPool:
    global _ORDER_BOOK_EVENT_POOL
    if _ORDER_BOOK_EVENT_POOL is None:
        _ORDER_POOL = ObjectPool(_order_book_event_factory, capacity)
    return _ORDER_POOL


def get_book_level_pool(capacity: int = 10_000) -> ObjectPool:
    global _BOOK_LEVEL_POOL
    if _BOOK_LEVEL_POOL is None:
        _BOOK_LEVEL_POOL = ObjectPool(lambda: BookLevel(price=0.0, size=0.0), capacity)
    return _BOOK_LEVEL_POOL

"""
message_bus.py — Event-driven message bus for AnatoliaX.
In-memory by default; Redis Stream optional (configure via env).
Inspired by Nautilus Trader's MessageBus.
"""
import asyncio
import os
from typing import Callable, Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timezone
from common.events import Event, EventType, RiskEvent, Command


class MessageBus:
    """
    Pub/sub message bus for decoupled component communication.
    Thread-safe for single-threaded asyncio; use asyncio.Queue for async.
    """

    def __init__(self, use_redis: bool = False):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._queue: Optional[asyncio.Queue] = None
        self._use_redis = use_redis
        self._history: List[Event] = []
        self._max_history = 10_000
        if use_redis:
            self._redis = self._init_redis()
        else:
            self._redis = None

    def _init_redis(self):
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            r.ping()
            return r
        except Exception:
            return None

    def subscribe(self, event_type: EventType, callback: Callable):
        """Bir event tipine callback kaydet."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Callback'i kaldır."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """Event yayınla. Tüm subscriber'ları senkron çağır."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for cb in self._subscribers.get(event.event_type, []):
            try:
                cb(event)
            except Exception as e:
                print(f"[BUS] Handler error for {event.event_type}: {e}")

        # Redis forward (fire-and-forget)
        if self._redis:
            try:
                self._redis.xadd("anatoliax:events", {"data": event.__repr__()})
            except Exception:
                pass

    def publish_async(self, event: Event):
        """Async context'lerde kullanmak için."""
        if self._queue is None:
            self._queue = asyncio.Queue()
        self._queue.put_nowait(event)

    async def start_async_consumer(self):
        """Async consumer loop."""
        if self._queue is None:
            self._queue = asyncio.Queue()
        while True:
            event = await self._queue.get()
            self.publish(event)

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Son event'leri getir."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def command(self, cmd: Command):
        """Komut yayınla (special event type)."""
        self.publish(Event(event_type=EventType.AGENT_DECISION, metadata={"command": cmd.instruction, "payload": cmd.payload}))

    def reset(self):
        """Test ve recovery için bus'ı temizle."""
        self._subscribers.clear()
        self._history.clear()
        if self._queue:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

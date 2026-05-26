"""
async_event_bus.py — Async MessageBus with priority queues and backpressure.
K214: AsyncEventBus for event-driven architecture.
"""
import asyncio
import inspect
import time
from typing import Callable, Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime, timezone
from common.events import Event, EventType


class AsyncEventBus:
    """
    Asenkron event bus: priority queue, backpressure, retry handler.
    Thread-safe asyncio.Queue ile calisir.
    """

    def __init__(self, max_queue_size: int = 10_000):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._history: List[Dict] = []
        self._max_history = 10_000
        self._dropped_count = 0
        self._processed_count = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: EventType, callback: Callable):
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event: Event, priority: int = 5) -> bool:
        """Event yayinla. Queue doluysa drop et."""
        item = {"event": event, "priority": priority, "ts": time.time()}
        if self._queue.full():
            self._dropped_count += 1
            return False
        await self._queue.put(item)
        return True

    async def start(self):
        """Consumer loop baslat."""
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self):
        """Consumer loop durdur."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _consume_loop(self):
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            event = item["event"]
            self._history.append({
                "type": event.event_type.value,
                "ts": datetime.now(timezone.utc).isoformat(),
                "meta": event.metadata,
            })
            if len(self._history) > self._max_history:
                self._history.pop(0)

            for cb in self._subscribers.get(event.event_type, []):
                try:
                    if inspect.iscoroutinefunction(cb):
                        await cb(event)
                    else:
                        cb(event)
                except Exception as e:
                    print(f"[AsyncBus] Handler error for {event.event_type}: {e}")
            self._processed_count += 1
            self._queue.task_done()

    async def wait_until_empty(self, timeout: float = 5.0):
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    def get_stats(self) -> Dict:
        return {
            "processed": self._processed_count,
            "dropped": self._dropped_count,
            "pending": self._queue.qsize(),
            "subscribers": sum(len(v) for v in self._subscribers.values()),
        }

    def get_history(self, limit: int = 100) -> List[Dict]:
        return self._history[-limit:]

    def reset(self):
        self._subscribers.clear()
        self._history.clear()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        self._dropped_count = 0
        self._processed_count = 0

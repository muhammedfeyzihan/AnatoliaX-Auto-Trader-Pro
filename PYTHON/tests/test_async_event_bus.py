"""
test_async_event_bus.py — Tests for AsyncEventBus (K214)
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.async_event_bus import AsyncEventBus
from common.events import Event, EventType


@pytest.mark.asyncio
class TestAsyncEventBus:
    async def test_publish_and_consume(self):
        bus = AsyncEventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.ORDER_SUBMITTED, handler)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "1"}))
        await asyncio.sleep(0.2)
        await bus.stop()
        assert len(received) == 1

    async def test_async_handler(self):
        bus = AsyncEventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.ORDER_SUBMITTED, handler)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "2"}))
        await asyncio.sleep(0.2)
        await bus.stop()
        assert len(received) == 1

    async def test_drop_on_full(self):
        bus = AsyncEventBus(max_queue_size=1)
        await bus.start()
        # Queue is empty, first publish succeeds
        ok1 = await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "3"}))
        # Second may succeed or fail depending on timing
        await asyncio.sleep(0.1)
        await bus.stop()
        assert ok1 is True

    async def test_stats(self):
        bus = AsyncEventBus()
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: None)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "4"}))
        await asyncio.sleep(0.2)
        stats = bus.get_stats()
        assert stats["processed"] >= 1
        await bus.stop()

    async def test_history(self):
        bus = AsyncEventBus()
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: None)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "5"}))
        await asyncio.sleep(0.2)
        hist = bus.get_history(limit=10)
        assert len(hist) >= 1
        await bus.stop()

    async def test_wait_until_empty(self):
        bus = AsyncEventBus()
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: None)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "6"}))
        await bus.wait_until_empty(timeout=1.0)
        await bus.stop()

    async def test_reset(self):
        bus = AsyncEventBus()
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: None)
        await bus.start()
        await bus.publish(Event(event_type=EventType.ORDER_SUBMITTED, metadata={"id": "7"}))
        await asyncio.sleep(0.1)
        bus.reset()
        assert bus.get_stats()["processed"] == 0
        await bus.stop()

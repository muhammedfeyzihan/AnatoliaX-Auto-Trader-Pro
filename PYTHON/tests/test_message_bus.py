"""
Test: PYTHON.common.message_bus + events
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.message_bus import MessageBus
from common.events import Event, EventType, OrderEvent, FillEvent, RiskEvent, Command


class TestMessageBus:
    def test_publish_subscribe(self):
        bus = MessageBus()
        received = []
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: received.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0))
        assert len(received) == 1
        assert received[0].symbol == "THYAO"

    def test_multiple_subscribers(self):
        bus = MessageBus()
        a, b = [], []
        bus.subscribe(EventType.ORDER_FILLED, lambda e: a.append(e))
        bus.subscribe(EventType.ORDER_FILLED, lambda e: b.append(e))
        bus.publish(FillEvent(order_id="o1", filled_size=100, avg_fill_price=103.0))
        assert len(a) == 1 and len(b) == 1

    def test_unsubscribe(self):
        bus = MessageBus()
        received = []
        handler = lambda e: received.append(e)
        bus.subscribe(EventType.ORDER_SUBMITTED, handler)
        bus.unsubscribe(EventType.ORDER_SUBMITTED, handler)
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO"))
        assert len(received) == 0

    def test_history(self):
        bus = MessageBus()
        for i in range(5):
            bus.publish(OrderEvent(order_id=f"o{i}", symbol="THYAO"))
        hist = bus.get_history(event_type=EventType.ORDER_SUBMITTED, limit=3)
        assert len(hist) == 3
        assert hist[-1].order_id == "o4"

    def test_reset(self):
        bus = MessageBus()
        bus.subscribe(EventType.ORDER_SUBMITTED, lambda e: None)
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO"))
        bus.reset()
        assert len(bus._subscribers) == 0
        assert len(bus._history) == 0

    def test_command(self):
        bus = MessageBus()
        received = []
        bus.subscribe(EventType.AGENT_DECISION, lambda e: received.append(e))
        bus.command(Command(instruction="SCAN_SIGNALS", payload={"symbols": ["THYAO"]}))
        assert len(received) == 1
        assert received[0].metadata["command"] == "SCAN_SIGNALS"


class TestEvents:
    def test_order_event_fields(self):
        e = OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0, order_type="limit", sl=99.0, tp=110.0)
        assert e.event_type == EventType.ORDER_SUBMITTED
        assert e.sl == 99.0
        assert e.tp == 110.0

    def test_risk_event(self):
        e = RiskEvent(check_type="exposure", passed=False, reason="limit exceeded", order_id="o1")
        assert e.passed is False
        assert e.order_id == "o1"

    def test_event_timestamp(self):
        from datetime import datetime, timezone
        e = Event(event_type=EventType.ORDER_ACCEPTED)
        assert isinstance(e.timestamp, datetime)
        assert e.timestamp.tzinfo is timezone.utc

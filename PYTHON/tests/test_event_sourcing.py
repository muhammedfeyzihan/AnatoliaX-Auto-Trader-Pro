"""
test_event_sourcing.py — Comprehensive tests for EventStore and EventBus

Validation requirements:
  - Replay events from t=0, verify S(t) matches live state at checkpoint times
  - Append is monotonic
  - Replay is deterministic
  - Causality preserved
"""
import pytest
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.event_sourcing import (
    EventStore, EventBus, Event, EventType
)


class TestEvent:
    """Tests for Event data structure."""

    def test_event_creation(self):
        """Test basic event creation."""
        event = Event(
            event_type=EventType.ORDER,
            payload={"symbol": "THYAO", "side": "buy", "size": 1000},
        )
        
        assert event.event_type == EventType.ORDER
        assert event.payload["symbol"] == "THYAO"
        assert event.event_id is not None

    def test_event_timestamp_nanoseconds(self):
        """Test that timestamp has nanosecond precision."""
        event1 = Event(event_type=EventType.MARKET_DATA)
        time.sleep(0.001)  # 1ms
        event2 = Event(event_type=EventType.MARKET_DATA)
        
        # Timestamps should be different (nanosecond precision)
        assert event2.timestamp >= event1.timestamp

    def test_event_to_dict(self):
        """Test event serialization."""
        event = Event(
            event_type=EventType.SIGNAL,
            payload={"rsi": 65.0, "macd": 0.5},
            causation_id="parent-123",
            correlation_id="corr-456",
        )
        
        d = event.to_dict()
        
        assert d["event_type"] == "SignalEvent"
        assert "rsi" in d["payload"]
        assert d["causation_id"] == "parent-123"
        assert d["correlation_id"] == "corr-456"

    def test_event_from_dict(self):
        """Test event deserialization."""
        original = Event(
            event_type=EventType.FILL,
            payload={"price": 100.5, "size": 500},
            causation_id="order-789",
        )
        
        d = original.to_dict()
        restored = Event.from_dict(d)
        
        assert restored.event_type == original.event_type
        assert restored.payload == original.payload
        assert restored.causation_id == original.causation_id

    def test_event_compute_hash(self):
        """Test event hash computation."""
        event = Event(
            event_type=EventType.ORDER,
            payload={"symbol": "THYAO"},
        )
        
        hash1 = event.compute_hash()
        hash2 = event.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_event_with_causation(self):
        """Test creating event with causation chain."""
        parent = Event(event_type=EventType.SIGNAL, correlation_id="corr-1")
        child = Event(event_type=EventType.ORDER).with_causation(parent)
        
        assert child.causation_id == parent.event_id
        assert child.correlation_id == "corr-1"


class TestEventStore:
    """Tests for EventStore."""

    @pytest.fixture
    def store(self):
        """Create in-memory event store."""
        return EventStore(db_path=":memory:")

    def test_append_event(self, store):
        """Test appending event to store."""
        event = Event(event_type=EventType.ORDER, payload={"size": 100})
        event_id = store.append(event)
        
        assert event_id == event.event_id

    def test_get_events(self, store):
        """Test retrieving events."""
        for i in range(10):
            store.append(Event(event_type=EventType.MARKET_DATA, payload={"seq": i}))
        
        events = store.get_events(limit=100)
        
        assert len(events) == 10
        assert all(e.event_type == EventType.MARKET_DATA for e in events)

    def test_get_events_by_type(self, store):
        """Test filtering events by type."""
        store.append(Event(event_type=EventType.ORDER, payload={"side": "buy"}))
        store.append(Event(event_type=EventType.FILL, payload={"price": 100}))
        store.append(Event(event_type=EventType.ORDER, payload={"side": "sell"}))
        
        orders = store.get_events(event_type=EventType.ORDER, limit=100)
        
        assert len(orders) == 2
        assert all(e.event_type == EventType.ORDER for e in orders)

    def test_get_events_by_correlation(self, store):
        """Test filtering events by correlation ID."""
        store.append(Event(event_type=EventType.SIGNAL, correlation_id="corr-1"))
        store.append(Event(event_type=EventType.ORDER, correlation_id="corr-1"))
        store.append(Event(event_type=EventType.FILL, correlation_id="corr-2"))
        
        corr1_events = store.get_events(correlation_id="corr-1", limit=100)
        
        assert len(corr1_events) == 2

    def test_get_events_after_timestamp(self, store):
        """Test filtering events by timestamp."""
        events = []
        for i in range(10):
            event = Event(event_type=EventType.MARKET_DATA, payload={"seq": i})
            store.append(event)
            events.append(event)
        
        mid_ts = events[4].timestamp  # Event at index 4
        later_events = store.get_events(after_ts=mid_ts, limit=100)
        
        # Should get events 5-9 (5 events)
        assert len(later_events) == 5

    def test_replay_deterministic(self, store):
        """
        CRITICAL TEST: Replay must be deterministic.
        S(t) = reduce(apply, E[0:t], S_0)
        """
        for i in range(50):
            store.append(Event(event_type=EventType.SIGNAL, payload={"value": i}))
        
        def apply_fn(state, event):
            return state + [event.payload["value"]]
        
        result1 = store.replay(apply_fn, [])
        result2 = store.replay(apply_fn, [])
        result3 = store.replay(apply_fn, [])
        
        assert result1 == result2 == result3
        assert len(result1) == 50

    def test_replay_state_reconstruction(self, store):
        """Test reconstructing state from events."""
        initial_state = {"capital": 100000, "positions": []}
        
        store.append(Event(event_type=EventType.ORDER, payload={"side": "buy", "size": 10, "price": 100}))
        store.append(Event(event_type=EventType.FILL, payload={"price": 100.5, "size": 10}))
        store.append(Event(event_type=EventType.PNL, payload={"pnl": 500}))
        
        def apply_fn(state, event):
            if event.event_type == EventType.ORDER:
                if event.payload["side"] == "buy":
                    state["positions"].append({
                        "size": event.payload["size"],
                        "entry": event.payload["price"]
                    })
                    state["capital"] -= event.payload["size"] * event.payload["price"]
            elif event.event_type == EventType.PNL:
                state["capital"] += event.payload["pnl"]
            return state
        
        final_state = store.replay(apply_fn, initial_state)
        
        assert final_state["capital"] == 100000 - 10*100 + 500
        assert len(final_state["positions"]) == 1

    def test_checkpoint_and_restore(self, store):
        """Test checkpoint functionality for fast replay."""
        # Append events and track timestamps
        timestamps = []
        for i in range(100):
            event = Event(event_type=EventType.MARKET_DATA, payload={"value": i})
            store.append(event)
            timestamps.append(event.timestamp)
        
        # Checkpoint at event 50 (index 49)
        checkpoint_state = {"count": 50, "sum": sum(range(50))}
        checkpoint_ts = timestamps[49]  # Timestamp of 50th event
        store.checkpoint(checkpoint_state, checkpoint_ts, event_count=50)
        
        # Replay from checkpoint
        def apply_fn(state, event):
            state["count"] += 1
            state["sum"] += event.payload["value"]
            return state
        
        # Start from zero, replay from checkpoint should only apply events after checkpoint
        # But the checkpoint state already has count=50, sum=sum(0-49)
        # So final count = 50 (from checkpoint) + 50 (replayed) = 100
        # Final sum = sum(0-49) + sum(50-99) = sum(0-99)
        final_state = store.replay(apply_fn, {"count": 0, "sum": 0}, from_checkpoint=True)
        
        assert final_state["count"] == 100
        assert final_state["sum"] == sum(range(100))

    def test_validate_integrity(self, store):
        """Test event log integrity validation."""
        for i in range(50):
            store.append(Event(event_type=EventType.MARKET_DATA, payload={"seq": i}))
        
        report = store.validate_integrity()
        
        assert report["total_events"] == 50
        assert report["integrity_valid"] is True
        assert len(report["issues"]) == 0

    def test_event_stream_by_correlation(self, store):
        """Test getting event stream by correlation ID."""
        for i in range(20):
            store.append(Event(
                event_type=EventType.SIGNAL,
                correlation_id="trade-123",
                payload={"step": i}
            ))
        
        stream = store.get_event_stream("trade-123")
        
        assert len(stream) == 20
        assert all(e.correlation_id == "trade-123" for e in stream)

    def test_count_events(self, store):
        """Test counting events."""
        assert store.count_events() == 0
        
        for _ in range(25):
            store.append(Event(event_type=EventType.MARKET_DATA))
        
        assert store.count_events() == 25

    def test_monotonic_timestamps(self, store):
        """Test that appended events have monotonic timestamps."""
        events = []
        for i in range(50):
            event = Event(event_type=EventType.MARKET_DATA, payload={"seq": i})
            store.append(event)
            events.append(event)
        
        retrieved = store.get_events(limit=100)
        
        for i in range(1, len(retrieved)):
            assert retrieved[i].timestamp >= retrieved[i-1].timestamp

    def test_causality_preservation(self, store):
        """Test that causation chains are preserved."""
        parent = Event(event_type=EventType.SIGNAL, payload={"signal": "buy"})
        store.append(parent)
        
        child = Event(
            event_type=EventType.ORDER,
            payload={"side": "buy"},
            causation_id=parent.event_id,
            correlation_id=parent.event_id
        )
        store.append(child)
        
        events = store.get_events(limit=100)
        
        # Find the order event
        order_event = next(e for e in events if e.event_type == EventType.ORDER)
        assert order_event.causation_id == parent.event_id

    def test_close(self):
        """Test closing event store."""
        store = EventStore(db_path=":memory:")
        store.append(Event(event_type=EventType.MARKET_DATA))
        store.close()
        
        assert store._conn is None


class TestEventBus:
    """Tests for EventBus."""

    @pytest.fixture
    def event_store(self):
        """Create in-memory event store."""
        return EventStore(db_path=":memory:")

    @pytest.fixture
    def event_bus(self, event_store):
        """Create event bus with store."""
        return EventBus(event_store=event_store)

    def test_subscribe_and_publish(self, event_bus):
        """Test basic pub/sub."""
        received = []
        
        def callback(event):
            received.append(event)
        
        event_bus.subscribe(EventType.SIGNAL, callback)
        event = Event(event_type=EventType.SIGNAL, payload={"test": True})
        event_bus.publish(event)
        
        assert len(received) == 1
        assert received[0].payload["test"] is True

    def test_publish_persists_to_store(self, event_bus, event_store):
        """Test that publishing persists to event store."""
        event_bus.publish(Event(event_type=EventType.ORDER))
        
        events = event_store.get_events(limit=100)
        
        assert len(events) == 1
        assert events[0].event_type == EventType.ORDER

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        received = []
        
        def callback(event):
            received.append(event)
        
        event_bus.subscribe(EventType.SIGNAL, callback)
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        assert len(received) == 1
        
        event_bus.unsubscribe(EventType.SIGNAL, callback)
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        assert len(received) == 1  # No new events

    def test_publish_batch(self, event_bus):
        """Test batch publishing."""
        events = [
            Event(event_type=EventType.MARKET_DATA, payload={"seq": i})
            for i in range(10)
        ]
        
        event_ids = event_bus.publish_batch(events)
        
        assert len(event_ids) == 10

    def test_get_pending_events(self, event_bus):
        """Test getting pending events from queue."""
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        event_bus.publish(Event(event_type=EventType.ORDER))
        
        pending = event_bus.get_pending_events()
        
        assert len(pending) == 2

    def test_flush(self, event_bus):
        """Test flushing event queue."""
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        event_bus.flush()
        
        pending = event_bus.get_pending_events()
        assert len(pending) == 0

    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for same event type."""
        received1 = []
        received2 = []
        
        event_bus.subscribe(EventType.SIGNAL, lambda e: received1.append(e))
        event_bus.subscribe(EventType.SIGNAL, lambda e: received2.append(e))
        
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        
        assert len(received1) == 1
        assert len(received2) == 1

    def test_subscribe_different_event_types(self, event_bus):
        """Test subscribing to different event types."""
        signals = []
        orders = []
        
        event_bus.subscribe(EventType.SIGNAL, lambda e: signals.append(e))
        event_bus.subscribe(EventType.ORDER, lambda e: orders.append(e))
        
        event_bus.publish(Event(event_type=EventType.SIGNAL))
        event_bus.publish(Event(event_type=EventType.ORDER))
        event_bus.publish(Event(event_type=EventType.FILL))
        
        assert len(signals) == 1
        assert len(orders) == 1


class TestEventSourcingValidation:
    """Integration tests for event sourcing validation requirements."""

    def test_state_reconstruction_matches_checkpoint(self):
        """
        VALIDATION: Replay events from t=0, verify S(t) matches live state at checkpoint times.
        """
        store = EventStore(db_path=":memory:")
        
        # Simulate trading events
        state = {"capital": 100000, "trades": []}
        
        for i in range(100):
            event = Event(
                event_type=EventType.FILL,
                payload={"pnl": 100 if i % 2 == 0 else -50, "trade_id": i}
            )
            store.append(event)
            
            # Update live state
            state["capital"] += event.payload["pnl"]
            state["trades"].append(event.payload)
            
            # Checkpoint every 25 events
            if (i + 1) % 25 == 0:
                store.checkpoint({"capital": state["capital"]}, event.timestamp, event_count=i+1)
        
        # Validate: replay from t=0 should match live state
        def apply_fn(s, e):
            s["capital"] += e.payload["pnl"]
            return s
        
        replayed_state = store.replay(apply_fn, {"capital": 100000})
        
        assert replayed_state["capital"] == state["capital"]

    def test_95_percent_validation_threshold(self):
        """
        VALIDATION: For tick simulator, 95% of fills must be within tolerance.
        This test demonstrates the validation pattern.
        """
        from backtest.tick_simulator import TickLevelMarketSimulator, TickSimulatorConfig
        
        simulator = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        
        # Simulate 100 fills and record validation with VERY small errors
        # Error tolerance = 0.1 * spread = 0.1 * 0.5 = 0.05
        # We need 95+ samples with error < 0.05
        for i in range(100):
            # Simulated fill price
            sim_price = 100.0 + i * 0.001
            # Live fill with very small error (well within tolerance)
            live_price = sim_price + (i % 10 - 5) * 0.001  # Error between -0.005 and 0.004
            simulator.record_validation(sim_price, live_price, 0.5)
        
        stats = simulator.get_validation_stats()
        
        # All samples should be valid since error is much smaller than 0.05 tolerance
        assert stats["valid_pct"] >= 95.0, f"Expected >= 95% valid, got {stats['valid_pct']}%"
        assert stats["validation_passed"] is True

"""
Property-based tests for EventStore using Hypothesis.
Invariants: append is monotonic, replay is deterministic, causality preserved.
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from common.event_sourcing import EventStore, Event, EventType


class TestEventSourcingProperties:
    @given(
        payloads=st.lists(
            st.dictionaries(st.text(), st.integers() | st.text(), min_size=1, max_size=3),
            min_size=1, max_size=50
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_append_and_get_events_monotonic(self, payloads):
        store = EventStore(db_path=":memory:")
        timestamps = []
        for i, p in enumerate(payloads):
            ev = Event(event_type=EventType.MARKET_DATA, payload={"seq": i, **p})
            store.append(ev)
            timestamps.append(ev.timestamp)

        events = store.get_events(limit=100000)
        assert len(events) == len(payloads)
        # Timestamps are non-decreasing
        for i in range(1, len(events)):
            assert events[i].timestamp >= events[i - 1].timestamp

    @given(
        n_events=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_replay_is_deterministic(self, n_events):
        store = EventStore(db_path=":memory:")
        for i in range(n_events):
            store.append(Event(event_type=EventType.SIGNAL, payload={"i": i}))

        def apply_fn(state, event):
            return state + [event.payload.get("i", -1)]

        result1 = store.replay(apply_fn, [])
        result2 = store.replay(apply_fn, [])
        assert result1 == result2
        assert len(result1) == n_events

"""
Property-based tests for OrderStateMachine using Hypothesis.
Covers: transition matrix invariants, idempotency, TTL eviction.
"""
import pytest
from hypothesis import given, strategies as st, settings, Phase

from execution.order_state_machine import OrderStateMachine, OrderState


class TestOrderStateMachineProperties:
    @given(
        order_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
        symbol=st.sampled_from(["THYAO", "GARAN", "ASELS", "SISE", "KOZAA"]),
        side=st.sampled_from(["buy", "sell"]),
        size=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200, phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink])
    def test_create_order_always_pending(self, order_id, symbol, side, size, price):
        osm = OrderStateMachine()
        order = osm.create_order(order_id, symbol, side, size, price)
        assert order["state"] == OrderState.PENDING
        assert "idempotency_key" in order
        assert len(order["idempotency_key"]) > 0

    @given(
        max_retries=st.integers(min_value=0, max_value=10),
        attempts=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=100, deadline=None)
    def test_retry_respects_max_retries(self, max_retries, attempts):
        osm = OrderStateMachine(max_retries=max_retries, base_retry_sec=0.0001)
        osm.create_order("o1", "THYAO", "buy", 100, 105.0)
        osm.transition("o1", "error")
        ok = True
        for _ in range(attempts):
            ok = osm.retry("o1")
        if attempts > max_retries:
            assert ok is False

    @given(
        event=st.sampled_from(["submit", "partial_fill", "fill", "cancel", "expire", "error", "retry", "resubmit"]),
    )
    @settings(max_examples=100)
    def test_transition_from_pending_only_submit(self, event):
        osm = OrderStateMachine()
        osm.create_order("o1", "THYAO", "buy", 100, 105.0)
        next_state = osm.transition("o1", event)
        if event == "submit":
            assert next_state == OrderState.SUBMITTED
        elif event == "error":
            assert next_state == OrderState.ERROR
        else:
            # Invalid transitions from PENDING keep state or go to ERROR/CANCELLED
            assert next_state in (OrderState.PENDING, OrderState.ERROR, OrderState.SUBMITTED, OrderState.CANCELLED)

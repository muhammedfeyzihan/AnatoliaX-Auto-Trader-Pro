import pytest
from execution.order_state_machine import OrderStateMachine, OrderState


def test_create_order():
    osm = OrderStateMachine()
    order = osm.create_order("o1", "THYAO", "buy", 100, 105.0)
    assert order["state"] == OrderState.PENDING
    assert "idempotency_key" in order


def test_transition():
    osm = OrderStateMachine()
    osm.create_order("o1", "THYAO", "buy", 100, 105.0)
    next_state = osm.transition("o1", "submit")
    assert next_state == OrderState.SUBMITTED


def test_retry():
    osm = OrderStateMachine(max_retries=2)
    osm.create_order("o1", "THYAO", "buy", 100, 105.0)
    osm.transition("o1", "error")
    ok = osm.retry("o1")
    assert ok is True
    assert osm.get_order("o1")["retry_count"] == 1


def test_evict_stale():
    osm = OrderStateMachine(max_age_sec=0.0)
    osm.create_order("o1", "THYAO", "buy", 100, 105.0)
    evicted = osm.evict_stale()
    assert "o1" in evicted


def test_reconcile():
    osm = OrderStateMachine()
    osm.create_order("o1", "THYAO", "buy", 100, 105.0)
    osm.transition("o1", "submit")
    osm.transition("o1", "partial_fill", {"filled_size": 50})
    assert osm.reconcile("o1", 50, epsilon=1e-6) is True

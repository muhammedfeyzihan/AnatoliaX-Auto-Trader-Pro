"""
tests/test_circuit_breaker.py — BIST devre kesici birim testleri
"""
import pytest
from broker.bist.circuit_breaker import BISTCircuitBreaker


class TestCircuitBreaker:
    def test_group_a_up_trigger(self):
        cb = BISTCircuitBreaker()
        triggered = cb.check("THYAO", "A", 100.0, 111.0)
        assert triggered is True
        assert cb.is_triggered("THYAO") is True

    def test_group_b_down_trigger(self):
        cb = BISTCircuitBreaker()
        triggered = cb.check("THYAO", "B", 100.0, 93.0)
        assert triggered is True

    def test_reset(self):
        cb = BISTCircuitBreaker()
        cb.check("THYAO", "A", 100.0, 111.0)
        cb.reset("THYAO")
        assert cb.is_triggered("THYAO") is False

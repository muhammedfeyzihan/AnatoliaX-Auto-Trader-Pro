"""
tests/test_ring_buffer.py — LockFreeRingBuffer birim testleri
"""
import pytest
from hft_pro.core.ring_buffer import LockFreeRingBuffer


class TestLockFreeRingBuffer:
    def test_push_pop(self):
        rb = LockFreeRingBuffer(capacity=1024, dtype="float64")
        rb.push(1.0)
        rb.push(2.0)
        assert rb.pop() == 1.0
        assert rb.pop() == 2.0

    def test_batch_push_pop(self):
        rb = LockFreeRingBuffer(capacity=1024, dtype="float64")
        rb.batch_push([1.0, 2.0, 3.0])
        assert rb.batch_pop(3) == [1.0, 2.0, 3.0]

    def test_utilization(self):
        rb = LockFreeRingBuffer(capacity=100, dtype="float64")
        rb.batch_push([1.0] * 10)
        assert rb.utilization() == 10

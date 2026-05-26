"""
tests/test_clock.py — HFTClock birim testleri
"""
import pytest
from hft_pro.core.clock import HFTClock


class TestHFTClock:
    def test_now_ns_monotonic(self):
        c = HFTClock()
        t1 = c.now_ns()
        t2 = c.now_ns()
        assert t2 >= t1

    def test_elapsed_ns_positive(self):
        c = HFTClock()
        c.tsc_calibrate()
        t0 = c.now_ns()
        import time
        time.sleep(0.001)
        elapsed = c.elapsed_ns(t0)
        assert elapsed >= 0

    def test_tsc_calibrate_does_not_crash(self):
        c = HFTClock()
        c.tsc_calibrate()

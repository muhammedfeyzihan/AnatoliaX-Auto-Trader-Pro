"""
Test: PYTHON.backtest.latency_simulator
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.latency_simulator import LatencySimulator


class TestLatencySimulator:
    def test_sample_within_bounds(self):
        sim = LatencySimulator(mean_ms=150, std_dev_ms=50, min_ms=50, max_ms=500)
        for _ in range(100):
            lat = sim.sample()
            assert 50 <= lat <= 500

    def test_distribution(self):
        sim = LatencySimulator()
        dist = sim.distribution(samples=500)
        assert dist["avg"] > 0
        assert dist["p50"] >= dist["min"]
        assert dist["p95"] <= dist["max"]

    def test_simulate(self):
        sim = LatencySimulator(mean_ms=10, min_ms=1, max_ms=20)
        lat = sim.simulate()
        assert lat >= 1

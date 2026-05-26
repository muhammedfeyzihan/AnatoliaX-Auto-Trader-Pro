"""
tests/test_backtest_replay.py — DeterministicReplay birim testleri
"""
import pytest
from hft_pro.backtest.replay_engine import DeterministicReplay, ReplayConfig


class TestBacktestReplay:
    def test_hash_consistency(self):
        config = ReplayConfig(seed=42)
        replay = DeterministicReplay("ticks.csv", config)
        r1 = replay.replay(lambda x: None, seed=42)
        r2 = replay.replay(lambda x: None, seed=42)
        assert r1.hash == r2.hash

    def test_benchmark_runs(self):
        config = ReplayConfig(seed=42)
        replay = DeterministicReplay("ticks.csv", config)
        bench = replay.benchmark(iterations=3)
        assert bench.mean_time_ms >= 0

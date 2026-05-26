"""
tests/test_benchmark.py — AccelerationBenchmark birim testleri
"""
import pytest
from acceleration.benchmarks.gpu_benchmark import AccelerationBenchmark


class TestAccelerationBenchmark:
    def test_run_all_returns_results(self):
        bench = AccelerationBenchmark()
        results = bench.run_all()
        assert len(results) == 4
        for r in results:
            assert r.name != ""
            assert r.cpu_time_ms >= 0
            assert r.gpu_time_ms >= 0

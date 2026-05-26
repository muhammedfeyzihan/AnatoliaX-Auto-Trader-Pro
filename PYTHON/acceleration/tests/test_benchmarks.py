"""
tests/test_benchmarks.py — Benchmark testleri
"""
import unittest
from PYTHON.acceleration.benchmarks.cpu_vs_gpu import CPUvsGPUBenchmark


class TestBenchmarks(unittest.TestCase):
    def test_benchmark(self):
        bm = CPUvsGPUBenchmark(iterations=10)
        res = bm.benchmark(lambda x: sum(x), lambda x: sum(x), [1.0]*100)
        self.assertIn("speedup", res)


if __name__ == "__main__":
    unittest.main()

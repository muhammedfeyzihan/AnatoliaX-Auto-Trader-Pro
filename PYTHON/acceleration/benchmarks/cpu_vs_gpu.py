"""
benchmarks/cpu_vs_gpu.py — CPU vs GPU benchmark karsilastirmasi
"""
import time
from typing import Callable


class CPUvsGPUBenchmark:
    """
    CPU ve GPU implementasyonlari arasinda hiz karsilastirmasi.

    Metrikler:
    - Speedup = CPU_time / GPU_time
    - Throughput = islem/saniye
    - Latency P50/P95/P99

    K185: 3x+ hizlanma hedefi; dusukse optimizasyon gerekir.
    """

    def __init__(self, iterations: int = 1000):
        self.iterations = iterations

    def benchmark(self, cpu_fn: Callable, gpu_fn: Callable, data) -> dict:
        t0 = time.perf_counter()
        for _ in range(self.iterations):
            cpu_fn(data)
        t_cpu = time.perf_counter() - t0

        t0 = time.perf_counter()
        for _ in range(self.iterations):
            gpu_fn(data)
        t_gpu = time.perf_counter() - t0

        speedup = t_cpu / t_gpu if t_gpu > 0 else float("inf")
        return {
            "cpu_ms": t_cpu * 1000,
            "gpu_ms": t_gpu * 1000,
            "speedup": speedup,
            "target_met": speedup >= 3.0,
        }

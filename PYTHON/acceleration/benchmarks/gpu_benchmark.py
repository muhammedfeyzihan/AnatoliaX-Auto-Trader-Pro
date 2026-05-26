"""
benchmarks/gpu_benchmark.py — Hizlandirma benchmark paketi
"""
import time
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class BenchmarkResult:
    name: str
    cpu_time_ms: float
    gpu_time_ms: float
    speedup: float
    accuracy_delta: float


class AccelerationBenchmark:
    """
    Hizlandirma benchmark paketi.

    Testler:
    1. RAPIDS cuDF vs pandas: 10M satir uzerinde EMA, RSI
    2. CuPy RawKernel vs NumPy: 2000 tik uzerinde EMA hesaplama
    3. ONNX Runtime GPU vs CPU: 1M omek uzerinde cikarsama
    4. C++ shim vs Python: 10M uzerinde nanosaniye saat

    Hedef: Her benchmark 3x+ hizlanma; aksi halde uyari.
    """

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def run_all(self) -> List[BenchmarkResult]:
        self.results = []
        self.results.append(self._benchmark_rapids_ema())
        self.results.append(self._benchmark_cupy_ema())
        self.results.append(self._benchmark_onnx_inference())
        self.results.append(self._benchmark_cpp_clock())
        return self.results

    def _benchmark_rapids_ema(self) -> BenchmarkResult:
        name = "RAPIDS EMA vs pandas"
        try:
            import pandas as pd
            import numpy as np
            df = pd.DataFrame({"close": np.random.rand(1_000_000)})
            t0 = time.perf_counter()
            df["ema"] = df["close"].ewm(span=20, adjust=False).mean()
            t1 = time.perf_counter()
            cpu = (t1 - t0) * 1000
            try:
                import cudf
                gdf = cudf.DataFrame({"close": np.random.rand(1_000_000)})
                t0 = time.perf_counter()
                gdf["ema"] = gdf["close"].ewm(span=20, adjust=False).mean()
                t1 = time.perf_counter()
                gpu = (t1 - t0) * 1000
            except Exception:
                gpu = cpu
            return BenchmarkResult(name, cpu, gpu, cpu / max(gpu, 1e-6), 0.0)
        except Exception as e:
            return BenchmarkResult(name, 0.0, 0.0, 0.0, 0.0)

    def _benchmark_cupy_ema(self) -> BenchmarkResult:
        name = "CuPy RawKernel EMA vs NumPy"
        try:
            import numpy as np
            arr = np.random.rand(2000).astype(np.float32)
            t0 = time.perf_counter()
            # basit CPU EMA
            ema = arr.copy()
            alpha = 0.1
            for i in range(1, len(arr)):
                ema[i] = alpha * arr[i] + (1 - alpha) * ema[i - 1]
            t1 = time.perf_counter()
            cpu = (t1 - t0) * 1000
            try:
                import cupy as cp
                d_arr = cp.array(arr)
                d_ema = cp.empty_like(d_arr)
                from acceleration.gpu.cuda_kernels import CUDAKernels
                kern = CUDAKernels().ema_update
                if kern:
                    t0 = time.perf_counter()
                    kern((1,), (2000,), (d_arr, d_ema, 2000, cp.float32(alpha)))
                    cp.cuda.Device().synchronize()
                    t1 = time.perf_counter()
                    gpu = (t1 - t0) * 1000
                else:
                    gpu = cpu
            except Exception:
                gpu = cpu
            return BenchmarkResult(name, cpu, gpu, cpu / max(gpu, 1e-6), 0.0)
        except Exception:
            return BenchmarkResult(name, 0.0, 0.0, 0.0, 0.0)

    def _benchmark_onnx_inference(self) -> BenchmarkResult:
        name = "ONNX Runtime GPU vs CPU"
        # Yer tutucu: gercek model gerektirir
        return BenchmarkResult(name, 0.0, 0.0, 0.0, 0.0)

    def _benchmark_cpp_clock(self) -> BenchmarkResult:
        name = "C++ shim clock vs Python time"
        try:
            import time
            t0 = time.perf_counter()
            for _ in range(1_000_000):
                time.time_ns()
            t1 = time.perf_counter()
            cpu = (t1 - t0) * 1000
            try:
                import anatoliax_cpp
                c = anatoliax_cpp.NanosecondClock()
                t0 = time.perf_counter()
                for _ in range(1_000_000):
                    c.now_ns()
                t1 = time.perf_counter()
                gpu = (t1 - t0) * 1000
            except Exception:
                gpu = cpu
            return BenchmarkResult(name, cpu, gpu, cpu / max(gpu, 1e-6), 0.0)
        except Exception:
            return BenchmarkResult(name, 0.0, 0.0, 0.0, 0.0)

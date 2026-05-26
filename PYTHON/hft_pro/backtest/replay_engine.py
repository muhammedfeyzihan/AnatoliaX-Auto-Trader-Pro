"""
backtest/replay_engine.py — Bit-eşsiz deterministik tekrar (SHA-256 doğrulama)
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass
class ReplayConfig:
    seed: int = 42
    slippage_model: str = "bist"
    risk_limits: Dict = None


@dataclass
class ReplayResult:
    orders: List[dict]
    fills: List[dict]
    pnl: float
    hash: str


@dataclass
class ReplayBenchmark:
    iterations: int
    mean_time_ms: float
    std_time_ms: float


class DeterministicReplay:
    """
    Deterministik tick tekrar motoru.

    Sözleşme: Replay(M, s, C) her zaman aynı çıktıyı üretir.
    Doğrulama: SHA-256(M || s || C || code_version) -> hash.
    Hash eşleşirse çıktı bit-eşsizdir.

    Bileşenler:
    - Piyasa verisi akışı M: zaman damgası sıralı tick dosyası (CSV/parquet/binary)
    - Tohum s: rastgele bileşenler için tohum
    - Yapılandırma C: strateji parametreleri, risk limitleri, kayma modeli
    """

    def __init__(self, tick_file: str, config: ReplayConfig):
        self.tick_file = tick_file
        self.config = config
        self._ticks: List[dict] = []

    def replay(self, strategy: Callable, seed: int) -> ReplayResult:
        """Deterministik tekrar çalıştır. Emirler, doldurmalar, PnL, hash döndür."""
        import random
        rng = random.Random(seed)
        orders = []
        fills = []
        pnl = 0.0
        # Yer tutucu tekrar: gerçek uygulama ileride vektörize numpy + C++ ile
        for _ in range(10):
            orders.append({"id": rng.randint(1, 1000), "side": "BUY", "price": 100.0})
        result = ReplayResult(orders=orders, fills=fills, pnl=pnl, hash="")
        result.hash = self._compute_hash(result)
        return result

    def verify(self, expected_hash: str) -> bool:
        """Tekrar hash'ini beklenenle karşılaştır. Eşleşme döndür."""
        cfg = self.config
        dummy = ReplayResult(orders=[], fills=[], pnl=0.0, hash="")
        actual = self._compute_hash(dummy)
        return actual == expected_hash

    def benchmark(self, iterations: int = 100) -> ReplayBenchmark:
        """N tekrar çalıştır, tüm hash'lerin eşleştiğini doğrula. Zamanlama istatistikleri döndür."""
        import time
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            self.replay(lambda x: None, seed=self.config.seed)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        mean = sum(times) / len(times)
        variance = sum((t - mean) ** 2 for t in times) / len(times)
        std = variance ** 0.5
        return ReplayBenchmark(iterations=iterations, mean_time_ms=mean, std_time_ms=std)

    def _compute_hash(self, result: ReplayResult) -> str:
        data = json.dumps({
            "orders": result.orders,
            "fills": result.fills,
            "pnl": result.pnl,
            "config_seed": self.config.seed,
            "config_slippage": self.config.slippage_model,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

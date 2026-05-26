"""
latency_simulator.py — Gercekci Latency Simulasyonu (K134)
Normal dagilimli rastgele gecikme uretir.
"""
import random
import math
import time
from typing import Dict


class LatencySimulator:
    """
    Backtest'te gercekci latency ekler.
    Normal dagilim: mean=150ms, stdDev=50ms.
    """

    def __init__(self, mean_ms: float = 150, std_dev_ms: float = 50, min_ms: float = 50, max_ms: float = 500):
        self.mean = mean_ms
        self.std_dev = std_dev_ms
        self.min = min_ms
        self.max = max_ms

    def sample(self) -> float:
        """Box-Muller transform ile normal dagilimdan ornek."""
        u = random.random()
        v = random.random()
        z = math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)
        latency = self.mean + self.std_dev * z
        return max(self.min, min(self.max, latency))

    def simulate(self) -> float:
        delay = self.sample()
        time.sleep(delay / 1000)
        return delay

    def distribution(self, samples: int = 1000) -> Dict:
        values = sorted(self.sample() for _ in range(samples))
        avg = sum(values) / len(values)
        n = len(values)
        return {
            "avg": round(avg, 1),
            "p50": round(values[int(n * 0.5)], 1),
            "p95": round(values[int(n * 0.95)], 1),
            "p99": round(values[int(n * 0.99)], 1),
            "min": round(values[0], 1),
            "max": round(values[-1], 1),
        }

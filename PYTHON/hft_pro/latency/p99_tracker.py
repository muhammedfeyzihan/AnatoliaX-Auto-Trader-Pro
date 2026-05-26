"""
latency/p99_tracker.py — EWMA + quantile sketch (T-Digest) P50/P99/P999
"""
from typing import List


class P99Tracker:
    """
    EWMA + basit quantile izleyici.

    Algoritma:
    - EWMA: gecikme = alpha * yeni + (1-alpha) * eski
    - Quantile: siralama tabanli P50/P99/P999
    - Pencere: son N ornek (varsayilan 10k)

    K156: P999 > 1ms ise alarm tetikle.
    """

    def __init__(self, window: int = 10_000, alpha: float = 0.1):
        self.window = window
        self.alpha = alpha
        self._samples: List[float] = []
        self._ewma = 0.0

    def record(self, latency_ns: float) -> None:
        self._samples.append(latency_ns)
        if len(self._samples) > self.window:
            self._samples.pop(0)
        self._ewma = self.alpha * latency_ns + (1 - self.alpha) * self._ewma

    def p50(self) -> float:
        return self._quantile(0.50)

    def p99(self) -> float:
        return self._quantile(0.99)

    def p999(self) -> float:
        return self._quantile(0.999)

    def _quantile(self, q: float) -> float:
        if not self._samples:
            return 0.0
        s = sorted(self._samples)
        idx = int(len(s) * q)
        idx = min(idx, len(s) - 1)
        return s[idx]

    def alert_if_p999_exceeds(self, threshold_ns: float) -> bool:
        return self.p999() > threshold_ns

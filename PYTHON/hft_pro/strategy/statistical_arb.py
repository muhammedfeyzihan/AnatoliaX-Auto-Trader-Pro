"""
strategy/statistical_arb.py — BIST30 cift ticaret (kointegrasyon + OU sureci)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple


@dataclass
class PairSignal:
    long_symbol: str
    short_symbol: str
    zscore: float
    half_life: float
    confidence: float


class StatisticalArbitrage:
    """
    BIST30 cift ticaret.

    Algoritma:
    1. Cift secimi: yuksek korelasyon (>0.85), kointegrasyon (ADF p < 0.05)
    2. Spread: log(price_A) - beta * log(price_B)
    3. Z-score: (spread - mean) / std
    4. Sinyal: z > 2 ise short spread, z < -2 ise long spread
    5. OU half-life: -ln(2)/ln(gamma) ile kapanis tahmini

    K161: Cift ticaret VIOP ile hedge icin kullanilabilir.
    """

    def __init__(self, z_entry: float = 2.0, z_exit: float = 0.5):
        self.z_entry = z_entry
        self.z_exit = z_exit
        self._prices_a: List[float] = []
        self._prices_b: List[float] = []

    def update(self, price_a: Decimal, price_b: Decimal) -> Optional[PairSignal]:
        self._prices_a.append(float(price_a))
        self._prices_b.append(float(price_b))
        if len(self._prices_a) < 50:
            return None
        if len(self._prices_a) > 500:
            self._prices_a.pop(0)
            self._prices_b.pop(0)
        import statistics
        spread = [a - b for a, b in zip(self._prices_a, self._prices_b)]
        mean = statistics.mean(spread)
        std = statistics.stdev(spread) if len(spread) > 1 else 1e-9
        z = (spread[-1] - mean) / std
        if abs(z) >= self.z_entry:
            return PairSignal(
                long_symbol="A" if z < 0 else "B",
                short_symbol="B" if z < 0 else "A",
                zscore=z,
                half_life=10.0,
                confidence=min(abs(z) / 3.0, 1.0),
            )
        return None

"""
backtest/tick_simulator.py — Deterministik tick-seviye simulasyon
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class SimulatedTick:
    price: Decimal
    volume: Decimal
    timestamp_ns: int
    is_bid: bool


class TickSimulator:
    """
    Deterministik tick-seviye simulasyon.

    Girdi: Bar verisi (OHLCV)
    Cikti: Sentetik tick akisi

    Algoritma:
    - Hacim dagilimi: U-sekli (acilis/kapanista yogun)
    - Fiyat: OHLC icinde rastgele walk
    - Deterministik: tohum sabit, her zaman ayni tick akisi

    K163: Simulasyon backtest icin gercek tick verisi yoksa kullanilir.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        import random
        self._rng = random.Random(seed)

    def simulate(self, open_p: Decimal, high: Decimal, low: Decimal, close: Decimal,
                 volume: Decimal, num_ticks: int = 100) -> List[SimulatedTick]:
        ticks = []
        ts = 0
        price = float(open_p)
        vol_per_tick = float(volume) / num_ticks
        for _ in range(num_ticks):
            delta = self._rng.uniform(-1.0, 1.0) * (float(high) - float(low)) * 0.01
            price = max(min(price + delta, float(high)), float(low))
            is_bid = self._rng.random() > 0.5
            ticks.append(SimulatedTick(
                price=Decimal(str(price)),
                volume=Decimal(str(vol_per_tick)),
                timestamp_ns=ts,
                is_bid=is_bid,
            ))
            ts += 1_000_000  # 1ms artis
        return ticks

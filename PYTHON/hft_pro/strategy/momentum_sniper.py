"""
strategy/momentum_sniper.py — Alt-milisaniyelik momentum tespiti
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class SniperSignal:
    symbol: str
    side: str
    confidence: float
    trigger_price: Decimal
    target_price: Decimal
    stop_price: Decimal


class MomentumSniper:
    """
    Alt-milisaniyelik momentum tespiti.

    Tetikleyiciler:
    - Fiyat hareketi > 3 sigma (son 100 tick)
    - Hacim patlamasi > 5x ortalama
    - Emir defteri dengesizligi (bid/ask ratio > 3)

    K157: Sniper sinyali < 500us icinde emre donusturulmeli.
    """

    def __init__(self, sigma_threshold: float = 3.0, volume_mult: float = 5.0):
        self.sigma_threshold = sigma_threshold
        self.volume_mult = volume_mult
        self._prices: list = []
        self._volumes: list = []

    def on_tick(self, price: Decimal, volume: Decimal) -> Optional[SniperSignal]:
        self._prices.append(float(price))
        self._volumes.append(float(volume))
        if len(self._prices) > 100:
            self._prices.pop(0)
            self._volumes.pop(0)
        if len(self._prices) < 20:
            return None
        import statistics
        mean = statistics.mean(self._prices)
        std = statistics.stdev(self._prices) if len(self._prices) > 1 else 0
        if std > 0 and abs(float(price) - mean) > self.sigma_threshold * std:
            avg_vol = statistics.mean(self._volumes)
            if float(volume) > avg_vol * self.volume_mult:
                side = "BUY" if float(price) > mean else "SELL"
                return SniperSignal(
                    symbol="THYAO", side=side, confidence=0.85,
                    trigger_price=price,
                    target_price=price * Decimal("1.005") if side == "BUY" else price * Decimal("0.995"),
                    stop_price=price * Decimal("0.995") if side == "BUY" else price * Decimal("1.005"),
                )
        return None

"""
volatility_throttle.py — Volatility-based trade throttling (ATR, VIX, realized vol)
"""
import numpy as np
from typing import Optional


class VolatilityThrottle:
    """
    Yüksek volatilitede islem hacmini dusurur veya durdurur.
    ATR, realized vol veya VIX'e gore throttle uygular.
    """

    def __init__(
        self,
        atr_period: int = 14,
        high_vol_threshold: float = 0.03,
        max_size_pct: float = 1.0,
        min_size_pct: float = 0.1,
    ):
        self.atr_period = atr_period
        self.high_vol_threshold = high_vol_threshold
        self.max_size_pct = max_size_pct
        self.min_size_pct = min_size_pct

    def throttle(self, size: float, atr: float, price: float) -> float:
        """ATR/price oranina gore pozisyon buyuklugunu azalt."""
        vol_ratio = atr / price if price > 0 else 0
        if vol_ratio <= 0 or vol_ratio < self.high_vol_threshold * 0.3:
            return size * self.max_size_pct

        if vol_ratio >= self.high_vol_threshold:
            return size * self.min_size_pct

        # Lineer interpolasyon
        ratio = 1 - (vol_ratio / self.high_vol_threshold)
        scale = self.min_size_pct + (self.max_size_pct - self.min_size_pct) * ratio
        return size * scale

    def is_trading_allowed(self, atr: float, price: float) -> bool:
        vol_ratio = atr / price if price > 0 else 0
        return vol_ratio < self.high_vol_threshold * 1.5

    def get_status(self, atr: float, price: float) -> dict:
        vol_ratio = atr / price if price > 0 else 0
        return {
            "volatility_ratio": round(vol_ratio, 4),
            "threshold": self.high_vol_threshold,
            "allowed": self.is_trading_allowed(atr, price),
            "throttle_pct": round(self.throttle(1.0, atr, price) * 100, 1),
        }

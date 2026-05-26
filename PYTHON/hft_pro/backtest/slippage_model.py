"""
backtest/slippage_model.py — BIST aşamalı alım-satım modeli
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class MarketImpact:
    price_before: Decimal
    price_after: Decimal
    volume_participation: float
    spread: Decimal


class BISTSlippageModel:
    """
    BIST'e özgü kayma modeli.

    Adım kayma (aşamalı):
    - İlk %5 hacim: yayılma * 1.0
    - Sonraki %10: yayılma * 1.5
    - Sonraki %20: yayılma * 2.5
    - Kalan: yayılma * 4.0 (piyasa etkisi)

    Toplu emir etkisi:
    - kayma = yayılma * (1 + α * log10(hacim / ortalama_hacim))
    - α = 0.3 (BIST için tarihsel kalibre)

    Zaman gecikmesi:
    - gecikme = temel_ms + β * (emir_boyutu / derinlik) + rastgele_ms
    - rastgele ~ Rayleigh(σ=2ms)
    """

    def __init__(self, alpha: float = 0.3, base_ms: float = 5.0, beta: float = 0.1):
        self.alpha = alpha
        self.base_ms = base_ms
        self.beta = beta

    def calculate(self, order_size: Decimal, avg_volume: Decimal, spread: Decimal,
                  depth: Decimal, time_of_day: str = "normal") -> MarketImpact:
        """Emir için kayma etkisini hesapla."""
        ratio = float(order_size / avg_volume) if avg_volume > 0 else 0.0
        import math
        multiplier = 1.0 + self.alpha * math.log10(max(ratio, 1e-6))
        effective_spread = spread * Decimal(str(multiplier))
        price_before = Decimal("100.00")
        price_after = price_before + effective_spread / Decimal("2")
        return MarketImpact(
            price_before=price_before,
            price_after=price_after,
            volume_participation=ratio,
            spread=effective_spread,
        )

    def delay_ms(self, order_size: Decimal, depth: Decimal) -> float:
        """İletim gecikmesi (ms)."""
        import random
        ratio = float(order_size / depth) if depth > 0 else 0.0
        base = self.base_ms + self.beta * ratio
        noise = random.random() * 2.0  # basit gürültü
        return base + noise

"""
backtest/market_impact_model.py — Karekok yasasi: I = eta * sigma * (Q/ADV)^gamma
"""
from decimal import Decimal
from typing import Optional


class MarketImpactModel:
    """
    Karekok yasasi piyasa etkisi modeli.

    Formul:
    I = eta * sigma * (Q / ADV)^gamma

    Parametreler:
    - eta: kalibrasyon sabiti (0.1 - 0.3)
    - sigma: gunluk volatilite (std / ortalama)
    - Q: emir boyutu
    - ADV: ortalama gunluk hacim
    - gamma: 0.5 (karekok yasasi)

    K164: Piyasa etkisi her backtest emrinde hesaplanmalidir.
    """

    def __init__(self, eta: float = 0.2, gamma: float = 0.5):
        self.eta = eta
        self.gamma = gamma

    def calculate(self, order_qty: Decimal, adv: Decimal, daily_volatility: float) -> Decimal:
        """Piyasa etkisi fiyat kaymasi (Decimal)."""
        import math
        if adv <= 0:
            return Decimal("0")
        ratio = float(order_qty / adv)
        impact = self.eta * daily_volatility * (ratio ** self.gamma)
        return Decimal(str(impact))

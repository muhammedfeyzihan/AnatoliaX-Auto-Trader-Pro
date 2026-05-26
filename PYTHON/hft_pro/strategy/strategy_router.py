"""
strategy/strategy_router.py — Rejim-bilincli strateji secimi
"""
from enum import Enum, auto
from typing import Optional


class Regime(Enum):
    HIGH_VOLATILITY = auto()
    LOW_VOLATILITY = auto()
    TRENDING = auto()
    MEAN_REVERTING = auto()
    ILLIQUID = auto()


class StrategyRouter:
    """
    Rejim-bilincli strateji secimi.

    Rejim -> Strateji eslestirmesi:
    - YUKSEK_OYNAKLIK: MomentumSniper + yayilma genisletilmis
    - DUSUK_OYNAKLIK: MarketMaker (dar yayilma)
    - TREND: MomentumSniper (trend yonunde)
    - MEAN_REVERT: StatisticalArb (OU geri donusu)
    - DUSUK_HACIM: Pasif (kotasyonu azalt)

    K162: Regim degisimi > 0.8 ise strateji parametrelerini gecersiz kil.
    """

    def __init__(self):
        self._strategies = {
            Regime.HIGH_VOLATILITY: ["momentum_sniper", "spread_scalper"],
            Regime.LOW_VOLATILITY: ["market_maker"],
            Regime.TRENDING: ["momentum_sniper"],
            Regime.MEAN_REVERTING: ["statistical_arb"],
            Regime.ILLIQUID: [],
        }

    def select(self, regime: Regime) -> list:
        return self._strategies.get(regime, [])

    def on_regime_change(self, old: Regime, new: Regime, confidence: float) -> bool:
        """Regim degisimi > 0.8 ise stratejileri degistir."""
        return confidence > 0.8 and old != new

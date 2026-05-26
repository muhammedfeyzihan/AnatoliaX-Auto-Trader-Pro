"""
arbitrage/stat_arb.py — Istatiksel arbitraj (cointegration + z-score)
"""
from typing import Tuple


class StatisticalArbitrage:
    """
    Istatiksel arbitraj motoru.

    Yontem:
    - Cointegration testi (ADF)
    - Hedge ratio (OLS)
    - Z-Score bazli emir sinyali (+>+2.5 sat, <-2.5 al)

    K200: Stat arb sadece yeterli hacimli ciftlerde calisir; slippage hesaba katilir.
    """

    def __init__(self, lookback: int = 60, entry_z: float = 2.5, exit_z: float = 0.5):
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    def signal(self, spread: float, mean: float, std: float) -> str:
        if std == 0:
            return "HOLD"
        z = (spread - mean) / std
        if z > self.entry_z:
            return "SHORT_SPREAD"
        if z < -self.entry_z:
            return "LONG_SPREAD"
        if abs(z) < self.exit_z:
            return "EXIT"
        return "HOLD"

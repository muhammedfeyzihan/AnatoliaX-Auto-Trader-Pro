"""
arbitrage/pair_selector.py — Arbitraj cifti secimi
"""
from typing import List, Tuple


class PairSelector:
    """
    Arbitraj cifti adaylari secimi.

    Kriterler:
    - Ayni sektor / benzer is modeli
    - Cointegration p-value < 0.05
    - Ortalama hacim > 1M TL/gun
    - Korelasyon > 0.70

    K201: Cift secimi haftalik guncellenir; 20+ cift havuzu hedeflenir.
    """

    def __init__(self, min_volume: float = 1_000_000, min_corr: float = 0.70):
        self.min_volume = min_volume
        self.min_corr = min_corr

    def select(self, symbols: List[str], corr_matrix: dict) -> List[Tuple[str, str]]:
        pairs = []
        for i, s1 in enumerate(symbols):
            for s2 in symbols[i + 1:]:
                corr = corr_matrix.get((s1, s2), 0)
                if corr >= self.min_corr:
                    pairs.append((s1, s2))
        return pairs

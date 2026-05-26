"""
feed/arb_detector.py — Capraz besleme arbitraj tespiti (BIST <-> VIOP <-> Binance)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class ArbOpportunity:
    buy_venue: str
    sell_venue: str
    symbol: str
    buy_price: Decimal
    sell_price: Decimal
    spread_pct: float
    profit_potential: Decimal


class ArbDetector:
    """
    Coklu mekan arbitraj tespiti.

    Tespit:
    - BIST <-> VIOP: spot-vadeli farki (basis)
    - BIST <-> Binance: TRY/USD kur etkisiyle fiyat farki
    - Min spread esigi: %0.3 (komisyonlar dahil)

    K159: Arbitraj firsati tespit edildiginde strateji rotasi yap.
    """

    def __init__(self, min_spread_pct: float = 0.3):
        self.min_spread_pct = min_spread_pct
        self._latest: Dict[str, Dict[str, Decimal]] = {}

    def on_tick(self, tick, venue: str) -> None:
        """Tick'i mekan bazli kaydet."""
        sym = tick.symbol
        if sym not in self._latest:
            self._latest[sym] = {}
        self._latest[sym][venue] = tick.price

    def scan(self) -> List[ArbOpportunity]:
        """Tum sembollerde arbitraj firsati ara."""
        ops = []
        for sym, venues in self._latest.items():
            vnames = list(venues.keys())
            for i in range(len(vnames)):
                for j in range(i + 1, len(vnames)):
                    v1, v2 = vnames[i], vnames[j]
                    p1, p2 = venues[v1], venues[v2]
                    if p1 > 0 and p2 > 0:
                        spread = abs(float(p2 - p1) / float(p1)) * 100
                        if spread >= self.min_spread_pct:
                            if p1 < p2:
                                ops.append(ArbOpportunity(v1, v2, sym, p1, p2, spread, p2 - p1))
                            else:
                                ops.append(ArbOpportunity(v2, v1, sym, p2, p1, spread, p1 - p2))
        return ops

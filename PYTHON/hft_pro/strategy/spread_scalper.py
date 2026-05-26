"""
strategy/spread_scalper.py — Coklu mekan yayilma yakalama
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class SpreadSignal:
    symbol: str
    buy_venue: str
    sell_venue: str
    spread: Decimal
    expected_profit: Decimal


class SpreadScalper:
    """
    Coklu mekan yayilma yakalama.

    Mantik:
    - A mekaninda al, B mekaninda sat
    - Yayilma > (komisyon_A + komisyon_B + kayma + buffer)
    - Tutma suresi < 1 saniye (scalping)

    K160: Spread scalper otomatik yonlendirici ile calisir.
    """

    def __init__(self, min_spread_bps: float = 5.0, max_hold_ms: int = 1000):
        self.min_spread_bps = min_spread_bps
        self.max_hold_ms = max_hold_ms

    def scan(self, books: dict) -> List[SpreadSignal]:
        """Coklu defterlerden yayilma firsati ara."""
        signals = []
        venues = list(books.keys())
        for i in range(len(venues)):
            for j in range(i + 1, len(venues)):
                v1, v2 = venues[i], venues[j]
                b1, b2 = books[v1], books[v2]
                if b1.ask and b2.bid and b2.bid > b1.ask:
                    spread = b2.bid - b1.ask
                    bps = float(spread / b1.ask) * 10_000
                    if bps >= self.min_spread_bps:
                        signals.append(SpreadSignal("THYAO", v1, v2, spread, spread * Decimal("0.7")))
                if b2.ask and b1.bid and b1.bid > b2.ask:
                    spread = b1.bid - b2.ask
                    bps = float(spread / b2.ask) * 10_000
                    if bps >= self.min_spread_bps:
                        signals.append(SpreadSignal("THYAO", v2, v1, spread, spread * Decimal("0.7")))
        return signals

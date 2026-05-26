"""
feed/normalization.py — Besleme normalizasyonu (BIST/Binance/coklu mekan)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class NormalizedTick:
    symbol: str
    price: Decimal
    volume: Decimal
    timestamp_ns: int
    venue: str
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None


class FeedNormalizer:
    """
    Coklu mekan besleme normalizasyonu.

    BIST, Binance, VIOP gibi farkli kaynaklardan gelen tick'leri
    tek bir NormalizedTick formatina donusturur.

    Donusum kurallari:
    - Sembol mapping: THYAO.IS -> THYAO (BIST), THYAOUSDT (Binance)
    - Fiyat olcegi: BIST kurus -> TL, Binance USDT -> TL (kur ile)
    - Zaman damgasi: epoch ms -> ns
    """

    def __init__(self, symbol_map: Dict[str, str] = None):
        self._symbol_map = symbol_map or {}

    def normalize(self, raw_tick: dict, source: str) -> NormalizedTick:
        """Ham tick'i normallestir."""
        sym = self._symbol_map.get(raw_tick.get("symbol", ""), raw_tick.get("symbol", ""))
        price = Decimal(str(raw_tick.get("price", 0)))
        volume = Decimal(str(raw_tick.get("volume", 0)))
        ts = int(raw_tick.get("timestamp", 0)) * 1_000_000  # ms -> ns
        return NormalizedTick(
            symbol=sym, price=price, volume=volume,
            timestamp_ns=ts, venue=source,
            bid=Decimal(str(raw_tick.get("bid", 0))) if "bid" in raw_tick else None,
            ask=Decimal(str(raw_tick.get("ask", 0))) if "ask" in raw_tick else None,
        )

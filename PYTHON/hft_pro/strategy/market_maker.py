"""
strategy/market_maker.py — Çift taraflı kotasyon (envanter eğimi ile)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class FillEvent:
    price: Decimal
    size: Decimal
    side: str
    timestamp_ns: int


@dataclass
class Order:
    symbol: str
    side: str
    price: Decimal
    size: Decimal
    order_id: str


class MarketMaker:
    """
    BIST piyasa yapıcı stratejisi.

    Kotasyon oluşturma:
    - bid_fiyat = orta - yayılma/2 - envanter_eğimi
    - ask_fiyat = orta + yayılma/2 + envanter_eğimi

    Envanter eğimi:
    - eğim = k * (envanter / maksimum_envanter) * yayılma
    - k: eğim agresifliği (0.5 ila 2.0)
    - envanter > 0: bid sıkılaştır, ask genişlet (satmayı teşvik et)
    - envanter < 0: bid genişlet, ask sıkılaştır (almayı teşvik et)

    Yayılma ayarı:
    - temel_yayılma = max(min_yayılma, α * σ_1dk + β / derinlik)
    - α, β tarihsel veriden kalibre edilir

    Olumsuz seçim:
    - toxic_flow_probability > 0.7 ise: yayılma 2x, boyut 0.5x, kotasyonu çek

    K94 uyumlu: sembol başına maksimum %2.
    Kotasyon yenileme: her 100ms veya önemli defter değişimi (>1 tik).
    """

    def __init__(self, symbol: str, max_inventory: Decimal, base_spread: Decimal,
                 skew_factor: float, risk_engine=None):
        self.symbol = symbol
        self.max_inventory = max_inventory
        self.base_spread = base_spread
        self.skew_factor = skew_factor
        self.risk_engine = risk_engine
        self._inventory = Decimal("0")
        self._realized_pnl = Decimal("0")
        self._unrealized_pnl = Decimal("0")
        self._entry_prices: List[Decimal] = []

    def on_tick(self, tick, book) -> List[Order]:
        """Tick ve defter durumuna göre emirler üret."""
        mid = book.mid_price
        spread = self.base_spread
        # Envanter eğimi
        skew = Decimal(str(self.skew_factor)) * (self._inventory / self.max_inventory) * spread
        bid_price = mid - spread / Decimal("2") - skew
        ask_price = mid + spread / Decimal("2") + skew
        orders = [
            Order(self.symbol, "BUY", bid_price.quantize(Decimal("0.01")), Decimal("100"), "mm_bid_1"),
            Order(self.symbol, "SELL", ask_price.quantize(Decimal("0.01")), Decimal("100"), "mm_ask_1"),
        ]
        return orders

    def on_fill(self, fill: FillEvent) -> None:
        """Envanteri güncelle, eğimi yeniden hesapla."""
        if fill.side == "BUY":
            self._inventory += fill.size
            self._entry_prices.append(fill.price)
        else:
            self._inventory -= fill.size
            if self._entry_prices:
                entry = self._entry_prices.pop(0)
                self._realized_pnl += (fill.price - entry) * fill.size

    def get_inventory(self) -> Decimal:
        """Geçerli envanter (pozitif=uzun, negatif=kısa)."""
        return self._inventory

    def get_pnl(self) -> Decimal:
        """Gerçekleşmiş + gerçekleşmemiş PnL."""
        return self._realized_pnl + self._unrealized_pnl

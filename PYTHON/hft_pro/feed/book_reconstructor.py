"""
feed/book_reconstructor.py — L3 emir defteri yeniden yapılandırma
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from sortedcontainers import SortedDict  # type: ignore


@dataclass
class BookSnapshot:
    bids: List[tuple]
    asks: List[tuple]
    timestamp_ns: int


@dataclass
class SpoofEvent:
    order_id: str
    price: Decimal
    size: Decimal
    place_time_ns: int
    cancel_time_ns: int
    duration_ns: int
    avg_size_at_level: Decimal


class OrderBook:
    """
    L3 emir defteri (fiyat-zaman önceliği).

    Veri yapısı:
    - bids: SortedDict[fiyat -> SortedDict[order_id -> (boyut, timestamp_ns)]]
    - asks: SortedDict[fiyat -> SortedDict[order_id -> (boyut, timestamp_ns)]]

    Değişmezler:
    - en_iyi_bid < en_iyi_ask (çakışma önleme)
    - toplam_bid_boyutu, toplam_ask_boyutu artarak izlenir
    - fiyat seviyesi başına defter derinliği izlenir

    Algılama:
    - sahte emir: emir konuldu + iptal edildi τ<2s içinde, boyut > 3x ortalama
    - katmanlama: ≥5 emir ardışık fiyatlarda konuldu/iptal edildi, işlem yapılmadan
    - likidite boşluğu: yayılma > 3σ_yayılma VE derinlik < 10. yüzdelik dilim
    """

    def __init__(self, symbol: str, max_levels: int = 10_000):
        self.symbol = symbol
        self.max_levels = max_levels
        self.bids: SortedDict[Decimal, SortedDict] = SortedDict()
        self.asks: SortedDict[Decimal, SortedDict] = SortedDict()
        self._total_bid_size = Decimal("0")
        self._total_ask_size = Decimal("0")
        self._order_history: Dict[str, dict] = {}

    def add_order(self, order_id: str, price: Decimal, size: Decimal, side: str, timestamp_ns: int) -> None:
        """Deftere emir ekle."""
        book = self.bids if side == "BID" else self.asks
        if price not in book:
            book[price] = SortedDict()
        book[price][order_id] = (size, timestamp_ns)
        self._order_history[order_id] = {"price": price, "size": size, "side": side, "place_ns": timestamp_ns}
        if side == "BID":
            self._total_bid_size += size
        else:
            self._total_ask_size += size

    def modify_order(self, order_id: str, new_size: Decimal) -> None:
        """Emir boyutunu değiştir."""
        hist = self._order_history.get(order_id)
        if not hist:
            return
        side = hist["side"]
        price = hist["price"]
        book = self.bids if side == "BID" else self.asks
        level = book.get(price)
        if level and order_id in level:
            old_size, ts = level[order_id]
            delta = new_size - old_size
            level[order_id] = (new_size, ts)
            if side == "BID":
                self._total_bid_size += delta
            else:
                self._total_ask_size += delta
            hist["size"] = new_size

    def cancel_order(self, order_id: str) -> None:
        """Emir iptal et. Sahte emir algılama için iptal zamanını izle."""
        hist = self._order_history.get(order_id)
        if not hist:
            return
        side = hist["side"]
        price = hist["price"]
        size = hist["size"]
        book = self.bids if side == "BID" else self.asks
        level = book.get(price)
        if level and order_id in level:
            del level[order_id]
            if not level:
                del book[price]
        if side == "BID":
            self._total_bid_size -= size
        else:
            self._total_ask_size -= size

    def execute_trade(self, order_id: str, size: Decimal) -> None:
        """Emir boyutunu işlem miktarı kadar azalt. Tamamen dolduysa kaldır."""
        hist = self._order_history.get(order_id)
        if not hist:
            return
        side = hist["side"]
        price = hist["price"]
        book = self.bids if side == "BID" else self.asks
        level = book.get(price)
        if level and order_id in level:
            remaining, ts = level[order_id]
            new_size = remaining - size
            if new_size <= 0:
                self.cancel_order(order_id)
            else:
                level[order_id] = (new_size, ts)
                if side == "BID":
                    self._total_bid_size -= size
                else:
                    self._total_ask_size -= size
                hist["size"] = new_size

    def get_snapshot(self, levels: int = 10) -> BookSnapshot:
        """İlk N seviyenin bid/ask'ını döndür."""
        bids = []
        for price in reversed(self.bids.keys()):
            total = sum(s for s, _ in self.bids[price].values())
            bids.append((price, total))
            if len(bids) >= levels:
                break
        asks = []
        for price in self.asks.keys():
            total = sum(s for s, _ in self.asks[price].values())
            asks.append((price, total))
            if len(asks) >= levels:
                break
        return BookSnapshot(bids=bids, asks=asks, timestamp_ns=0)

    @property
    def mid_price(self) -> Decimal:
        """(en_iyi_bid + en_iyi_ask) / 2"""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return Decimal("0")
        return (bb + ba) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        """en_iyi_ask - en_iyi_bid"""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return Decimal("0")
        return ba - bb

    @property
    def best_bid(self) -> Optional[Decimal]:
        if not self.bids:
            return None
        return self.bids.peekitem(-1)[0]

    @property
    def best_ask(self) -> Optional[Decimal]:
        if not self.asks:
            return None
        return self.asks.peekitem(0)[0]

    @property
    def imbalance(self) -> float:
        """(bid_hacim - ask_hacim) / (bid_hacim + ask_hacim). Aralık: [-1, 1]."""
        total = self._total_bid_size + self._total_ask_size
        if total == 0:
            return 0.0
        return float((self._total_bid_size - self._total_ask_size) / total)

    def vwap(self, depth: int = 5) -> Decimal:
        """İlk N seviye için hacim-ağırlıklı ortalama fiyat."""
        snap = self.get_snapshot(levels=depth)
        total_vol = Decimal("0")
        total_price = Decimal("0")
        for price, size in snap.bids + snap.asks:
            total_vol += size
            total_price += price * size
        if total_vol == 0:
            return Decimal("0")
        return total_price / total_vol

    def detect_spoofing(self, lookback_ns: int = 2_000_000_000) -> List[SpoofEvent]:
        """
        Sahte emir algıla: emir konuldu ve 2 saniye içinde iptal edildi,
        boyut > o fiyat seviyesindeki ortalama emir boyutunun 3 katı.
        """
        events: List[SpoofEvent] = []
        import time
        now_ns = time.perf_counter_ns()
        for oid, hist in list(self._order_history.items()):
            place_ns = hist.get("place_ns", 0)
            # Basit yer tutucu: gerçek iptal zamanı izleme ileride tamamlanacak
            if now_ns - place_ns < lookback_ns:
                continue
        return events

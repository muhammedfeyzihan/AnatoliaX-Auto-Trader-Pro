"""
feed/feed_handler.py — Çoklu mekân besleme işleyici (çekirdek atlama desteği)
"""
import asyncio
import struct
from decimal import Decimal
from enum import Enum
from typing import Dict, List, NamedTuple, Optional

from hft_pro.core.ring_buffer import LockFreeRingBuffer


class Tick(NamedTuple):
    timestamp_ns: int
    venue: str
    symbol: str
    price: Decimal
    size: Decimal
    side: str
    flags: int
    sequence: int
    order_id: Optional[str]


class VenueConfig:
    def __init__(self, name: str, protocol: str, host: str, port: int):
        self.name = name
        self.protocol = protocol
        self.host = host
        self.port = port


class FeedHandler:
    """
    Çoklu mekân besleme işleyici (çekirdek atlama desteği).

    Mekânlar:
    - BIST: ITSP (İstanbul Ticaret Sistemi Protokolü) UDP çoklu yayın (Matriks/Gedik besleme)
    - VIOP: BIST türev besleme
    - Binance: futures WebSocket + UDP piyasa verisi
    - Interactive Brokers: TWS API (yedek)

    Ayrıştırma: Sıcak yol için C++ shim (feed_parser.so); normalizasyon: tüm mekânlar
    iç Tick biçimine çevrilir.
    """

    def __init__(self, venue_configs: List[VenueConfig]):
        self._configs = venue_configs
        self._buffers: Dict[str, LockFreeRingBuffer] = {}
        self._tasks: List[asyncio.Task] = []
        self._gap_stats: Dict[str, dict] = {}

    def start(self) -> None:
        """Tüm besleme iş parçacıklarını başlat. Mekân başına bir iş parçacığı."""
        for cfg in self._configs:
            self._buffers[cfg.name] = LockFreeRingBuffer(
                name=f"feed_rb_{cfg.name}", capacity=1_000_000, entry_size=64
            )
            self._gap_stats[cfg.name] = {"gaps": 0, "last_seq": 0}

    def get_ring_buffer(self, venue: str) -> LockFreeRingBuffer:
        """Belirtilen mekân için halka tamponu döndür."""
        return self._buffers[venue]

    def subscribe(self, symbols: List[str], venue: str) -> None:
        """Belirtilen mekânda sembollere abone ol."""
        # Yer tutucu: gerçek abonelik ileride protokole özgü uygulanır
        pass

    def gap_stats(self) -> Dict[str, dict]:
        """Mekân başına boşluk algılama istatistiklerini döndür."""
        return self._gap_stats

    def _parse_udp_packet(self, packet: bytes, venue: str) -> Optional[Tick]:
        """UDP paketini Tick'e ayrıştır."""
        # Basit yer tutucu: gerçek ayrıştırma C++ shim'de yapılacak
        if len(packet) < 32:
            return None
        try:
            ts = struct.unpack("Q", packet[:8])[0]
            price_val = struct.unpack("d", packet[8:16])[0]
            size_val = struct.unpack("d", packet[16:24])[0]
            return Tick(
                timestamp_ns=ts,
                venue=venue,
                symbol="UNKNOWN",
                price=Decimal(str(price_val)),
                size=Decimal(str(size_val)),
                side="TRADE",
                flags=0,
                sequence=0,
                order_id=None,
            )
        except Exception:
            return None

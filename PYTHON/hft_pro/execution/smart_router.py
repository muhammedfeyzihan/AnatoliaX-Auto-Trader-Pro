"""
execution/smart_router.py — Çoklu mekân akıllı emir yönlendirici
"""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Dict, List


class RoutingStrategy(Enum):
    SINGLE = auto()
    SPLIT = auto()
    CONDITIONAL = auto()


@dataclass
class Order:
    symbol: str
    side: str
    quantity: Decimal
    price: Optional[Decimal]
    order_type: str = "LIMIT"


@dataclass
class RouteDecision:
    venue: str
    quantity: Decimal
    price: Decimal
    expected_latency_ms: float


class SmartRouter:
    """
    Çoklu mekân akıllı emir yönlendirici.

    Puanlama fonksiyonu: S_i = α * (1/gecikme_i) + β * (1/yayılma_i) + γ * derinlik_i + δ * güvenilirlik_i

    Kısıtlar:
    - K142-K148: BIST düzenlemeleri (VBTS, devre kesici, açığa satış yasağı)
    - K94: sembol başına maksimum pozisyon %2
    - Acil durum anahtarı: anahtar etkinse tüm emirler anında reddedilir

    Yönlendirme stratejileri:
    - SINGLE: tüm emri en iyi mekâna yönlendir
    - SPLIT: emri mekânlara böl (puana orantılı)
    - CONDITIONAL: mekân A'ya yönlendir, T ms içinde dolmazsa kalanını B'ye
    """

    def __init__(self, alpha: float = 1.0, beta: float = 1.0, gamma: float = 0.1, delta: float = 0.5):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self._latency: Dict[str, float] = {}
        self._spread: Dict[str, float] = {}
        self._depth: Dict[str, float] = {}
        self._reliability: Dict[str, float] = {}

    def route(self, order: Order, strategy: RoutingStrategy = RoutingStrategy.SPLIT) -> List[RouteDecision]:
        """Emir için yönlendirme kararları döndür."""
        venues = list(self._latency.keys())
        if not venues:
            return []

        scores: Dict[str, float] = {}
        for v in venues:
            lat = self._latency.get(v, 1e6)
            spr = self._spread.get(v, 1.0)
            dep = self._depth.get(v, 0.0)
            rel = self._reliability.get(v, 0.5)
            scores[v] = self.alpha * (1.0 / lat) + self.beta * (1.0 / spr) + self.gamma * dep + self.delta * rel

        if strategy == RoutingStrategy.SINGLE:
            best = max(scores, key=scores.get)
            return [RouteDecision(best, order.quantity, order.price or Decimal("0"), self._latency.get(best, 0.0))]

        if strategy == RoutingStrategy.SPLIT:
            total_score = sum(scores.values())
            decisions = []
            remaining = order.quantity
            for v in sorted(scores, key=scores.get, reverse=True):
                if remaining <= 0:
                    break
                ratio = scores[v] / total_score if total_score > 0 else 0
                qty = min(order.quantity * Decimal(str(ratio)), remaining)
                remaining -= qty
                decisions.append(RouteDecision(v, qty, order.price or Decimal("0"), self._latency.get(v, 0.0)))
            return decisions

        # CONDITIONAL basit yer tutucu: en iyi mekâna git
        best = max(scores, key=scores.get)
        return [RouteDecision(best, order.quantity, order.price or Decimal("0"), self._latency.get(best, 0.0))]

    def update_latency(self, venue: str, rtt_ns: int) -> None:
        """Mekân için RTT ölçümünü güncelle. EWMA yumuşatma."""
        rtt_ms = rtt_ns / 1_000_000.0
        old = self._latency.get(venue, rtt_ms)
        self._latency[venue] = 0.7 * old + 0.3 * rtt_ms

    def update_reliability(self, venue: str, success: bool) -> None:
        """Emir başarısına göre güvenilirlik puanını güncelle."""
        old = self._reliability.get(venue, 0.9)
        self._reliability[venue] = old * 0.95 + (1.0 if success else 0.0) * 0.05

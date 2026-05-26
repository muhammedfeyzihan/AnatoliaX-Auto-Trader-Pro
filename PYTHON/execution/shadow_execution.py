"""
execution/shadow_execution.py — Shadow Execution Environment (Phase 1)
Module 18 from anatoliax_prompt_v6.txt

Features:
  - Parallel execution: for each live order O_live, create O_shadow with same parameters.
  - Divergence metric: d = |fill_live - fill_shadow| / spread.
  - Alert if d > threshold_d or latency_shadow > 1.5*latency_live.
  - Zero capital exposure: O_shadow routed to paper broker.
  - Real-time monitoring: divergence time series D(t) with EWMA smoothing.
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque


@dataclass
class ShadowOrder:
    live_order_id: str
    symbol: str
    side: str
    size: float
    price: float
    fill_price: Optional[float] = None
    latency_ms: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ShadowExecutionEnvironment:
    """
    Creates shadow orders for every live order, tracks divergence.
    """

    def __init__(self, divergence_threshold: float = 0.5, latency_ratio_threshold: float = 1.5):
        self.divergence_threshold = divergence_threshold
        self.latency_ratio_threshold = latency_ratio_threshold
        self._shadows: Dict[str, ShadowOrder] = {}
        self._divergence_series: deque = deque(maxlen=1000)
        self._ewma_alpha: float = 0.1
        self._ewma: float = 0.0

    def create_shadow(self, live_order_id: str, symbol: str, side: str, size: float, price: float):
        shadow = ShadowOrder(
            live_order_id=live_order_id,
            symbol=symbol,
            side=side,
            size=size,
            price=price,
        )
        self._shadows[live_order_id] = shadow
        return shadow

    def record_live_fill(self, live_order_id: str, fill_price: float, latency_ms: float):
        shadow = self._shadows.get(live_order_id)
        if not shadow:
            return
        shadow.fill_price = fill_price
        shadow.latency_ms = latency_ms

    def record_shadow_fill(self, live_order_id: str, fill_price: float, latency_ms: float, spread: float):
        shadow = self._shadows.get(live_order_id)
        if not shadow or not shadow.fill_price:
            return

        d = abs(shadow.fill_price - fill_price) / spread if spread > 0 else 0.0
        self._divergence_series.append(d)
        self._ewma = self._ewma_alpha * d + (1 - self._ewma_alpha) * self._ewma

        latency_ratio = latency_ms / shadow.latency_ms if shadow.latency_ms > 0 else 0.0
        return {
            "divergence": d,
            "divergence_alert": d > self.divergence_threshold,
            "latency_ratio": latency_ratio,
            "latency_alert": latency_ratio > self.latency_ratio_threshold,
            "ewma_divergence": self._ewma,
        }

    def get_divergence_stats(self) -> Dict:
        if not self._divergence_series:
            return {}
        return {
            "mean_divergence": statistics.mean(self._divergence_series),
            "max_divergence": max(self._divergence_series),
            "ewma": self._ewma,
            "sample_count": len(self._divergence_series),
        }

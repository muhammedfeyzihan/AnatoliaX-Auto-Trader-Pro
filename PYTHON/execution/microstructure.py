"""
execution/microstructure.py — Execution Microstructure Engine (Phase 1)
Module 1 from anatoliax_prompt_v6.txt

Features:
  - Queue position modeling: Q(t) = f(order_size, book_depth, arrival_rate)
  - Hidden liquidity detection via imbalance metrics
  - Iceberg order detection via size-clustering
  - Adverse selection analysis via realized spread
  - Smart order slicing: TWAP, VWAP, POV
  - Toxicity-aware execution routing via VPIN
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from enum import Enum


class SliceType(Enum):
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"


@dataclass
class MicrostructureState:
    symbol: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bid_vol: float = 0.0
    ask_vol: float = 0.0
    book_depth: float = 0.0
    arrival_rate: float = 0.0
    midprice: float = 0.0
    spread: float = 0.0
    vpin: float = 0.0


class QueuePositionModel:
    """Queue position modeling Q(t) = f(order_size, book_depth, arrival_rate)."""

    def estimate(self, order_size: float, book_depth: float, arrival_rate: float) -> float:
        if book_depth <= 0 or arrival_rate <= 0:
            return 0.0
        return min(1.0, order_size / (book_depth * arrival_rate))


class HiddenLiquidityDetector:
    """
    Hidden liquidity detection via imbalance metrics.
    I = (bid_vol - ask_vol) / (bid_vol + ask_vol)
    """

    def imbalance(self, bid_vol: float, ask_vol: float) -> float:
        denom = bid_vol + ask_vol
        if denom == 0:
            return 0.0
        return (bid_vol - ask_vol) / denom

    def detect_hidden_liquidity(self, state: MicrostructureState, threshold: float = 0.7) -> bool:
        """True if imbalance exceeds threshold (indicating hidden liquidity)."""
        i = self.imbalance(state.bid_vol, state.ask_vol)
        return abs(i) > threshold


class IcebergDetector:
    """
    Iceberg order detection via size-clustering algorithms.
    Detect repeated same-size orders that may be part of a larger iceberg.
    """

    def __init__(self, cluster_threshold: float = 0.15, min_cluster_size: int = 3):
        self.cluster_threshold = cluster_threshold
        self.min_cluster_size = min_cluster_size
        self._history: Dict[str, List[float]] = {}

    def record(self, symbol: str, size: float):
        self._history.setdefault(symbol, []).append(size)

    def detect(self, symbol: str) -> Optional[Dict]:
        sizes = self._history.get(symbol, [])
        if len(sizes) < self.min_cluster_size:
            return None

        # Simple clustering: find repeated similar sizes
        clusters: Dict[float, int] = {}
        for s in sizes[-20:]:
            found = False
            for c in list(clusters.keys()):
                if abs(s - c) / (c + 1e-9) < self.cluster_threshold:
                    clusters[c] += 1
                    found = True
                    break
            if not found:
                clusters[s] = 1

        for c, count in clusters.items():
            if count >= self.min_cluster_size:
                return {
                    "symbol": symbol,
                    "iceberg_size": c,
                    "cluster_count": count,
                    "total_estimated": c * count,
                }
        return None


class AdverseSelectionAnalyzer:
    """
    Adverse selection analysis via realized spread.
    RS = 2 * (execution_price - midprice_t+5min)
    """

    def realized_spread(
        self,
        execution_price: float,
        midprice_future: float,
    ) -> float:
        return 2.0 * (execution_price - midprice_future)

    def liquidity_fade(
        self,
        midprice_1min_after: float,
        midprice_at_fill: float,
        spread: float,
    ) -> float:
        if spread == 0:
            return 0.0
        return (midprice_1min_after - midprice_at_fill) / spread


class SmartSlicer:
    """
    Smart order slicing:
      TWAP: v_i = V / n
      VWAP: v_i = V * (w_i / sum(w))
      POV:  v_i = alpha * market_vol_i
    """

    def twap(self, total_volume: float, slices: int) -> List[float]:
        v = total_volume / slices
        return [v] * slices

    def vwap(self, total_volume: float, volume_weights: List[float]) -> List[float]:
        total_w = sum(volume_weights) or 1.0
        return [total_volume * (w / total_w) for w in volume_weights]

    def pov(self, market_volumes: List[float], participation_rate: float = 0.1) -> List[float]:
        return [participation_rate * mv for mv in market_volumes]


class ToxicityRouter:
    """
    Toxicity-aware execution routing via VPIN.
    If VPIN > threshold -> passive execution (limit orders).
    """

    def __init__(self, vpin_threshold: float = 0.7):
        self.vpin_threshold = vpin_threshold

    def route(self, vpin: float) -> str:
        return "passive" if vpin > self.vpin_threshold else "aggressive"

    def expected_fill_quality(
        self,
        order_size: float,
        queue_depth: float,
        volatility: float,
        spread: float,
    ) -> float:
        """
        E[fill_price] <= arrival_price + slippage_model(Q, sigma, V)
        slip = alpha_1*(size/Q) + alpha_2*sigma + alpha_3*S
        """
        alpha1, alpha2, alpha3 = 0.5, 0.3, 0.2
        slip = alpha1 * (order_size / (queue_depth + 1e-9)) + alpha2 * volatility + alpha3 * spread
        return slip


class ExecutionMicrostructureEngine:
    """
    Orchestrates all microstructure modules into a single API.
    """

    def __init__(self, vpin_threshold: float = 0.7):
        self.queue = QueuePositionModel()
        self.hidden = HiddenLiquidityDetector()
        self.iceberg = IcebergDetector()
        self.adverse = AdverseSelectionAnalyzer()
        self.slicer = SmartSlicer()
        self.router = ToxicityRouter(vpin_threshold)

    def analyze_state(self, state: MicrostructureState) -> Dict:
        return {
            "queue_position": self.queue.estimate(
                order_size=state.book_depth * 0.1,
                book_depth=state.book_depth,
                arrival_rate=state.arrival_rate,
            ),
            "imbalance": self.hidden.imbalance(state.bid_vol, state.ask_vol),
            "hidden_liquidity": self.hidden.detect_hidden_liquidity(state),
            "vpin": state.vpin,
            "route": self.router.route(state.vpin),
            "expected_slippage": self.router.expected_fill_quality(
                order_size=state.book_depth * 0.1,
                queue_depth=state.book_depth,
                volatility=state.spread / (state.midprice + 1e-9),
                spread=state.spread,
            ),
        }

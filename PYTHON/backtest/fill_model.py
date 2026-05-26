"""
fill_model.py — Probabilistic fill model for event-driven backtests.
Inspired by Nautilus Trader's ThreeTierFillModel.
"""
import random
from abc import ABC, abstractmethod
from typing import Dict, Optional


class FillModel(ABC):
    """Abstract fill model protocol."""

    @abstractmethod
    def can_fill(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> bool:
        """Return True if order can be filled at this price."""
        pass

    @abstractmethod
    def fill_price(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> float:
        """Return actual fill price (may include slippage/impact)."""
        pass


class ImmediateFillModel(FillModel):
    """Always fills immediately at requested price."""

    def can_fill(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> bool:
        return True

    def fill_price(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> float:
        return price


class ThreeTierFillModel(FillModel):
    """
    Probabilistic fill model with three tiers:
    - Tier 1 (best bid/ask): High fill probability, minimal slippage
    - Tier 2 (next level): Medium fill probability, moderate slippage
    - Tier 3 (beyond): Low/no fill probability

    Parameters:
        tier1_prob: Fill probability at best level (default 0.95)
        tier2_prob: Fill probability at next level (default 0.50)
        tier1_slip: Slippage at tier 1 (%)
        tier2_slip: Slippage at tier 2 (%)
        participation_limit: Max % of book_depth that can be filled
    """

    def __init__(
        self,
        tier1_prob: float = 0.95,
        tier2_prob: float = 0.50,
        tier1_slip_pct: float = 0.001,
        tier2_slip_pct: float = 0.003,
        participation_limit: float = 0.10,
        seed: Optional[int] = None,
    ):
        self.tier1_prob = tier1_prob
        self.tier2_prob = tier2_prob
        self.tier1_slip = tier1_slip_pct
        self.tier2_slip = tier2_slip_pct
        self.participation_limit = participation_limit
        self._rng = random.Random(seed)

    def can_fill(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> bool:
        # Participation limit check
        if book_depth > 0 and (order_size / book_depth) > self.participation_limit:
            return False

        # Tier 1: Best level
        if self._rng.random() < self.tier1_prob:
            return True

        # Tier 2: Next level
        if self._rng.random() < self.tier2_prob:
            return True

        # Tier 3: No fill
        return False

    def fill_price(self, price: float, side: str, order_size: float, book_depth: float = 0.0) -> float:
        if not self.can_fill(price, side, order_size, book_depth):
            return 0.0

        # Determine tier based on first random draw
        r = self._rng.random()
        if r < self.tier1_prob:
            slip = self.tier1_slip
        elif r < self.tier1_prob + (1 - self.tier1_prob) * self.tier2_prob:
            slip = self.tier2_slip
        else:
            slip = self.tier2_slip * 2  # Fallback, should rarely happen

        if side.upper() == "BUY":
            return price * (1 + slip)
        elif side.upper() == "SELL":
            return price * (1 - slip)
        return price

    def get_stats(self) -> Dict[str, float]:
        return {
            "tier1_prob": self.tier1_prob,
            "tier2_prob": self.tier2_prob,
            "tier1_slip": self.tier1_slip,
            "tier2_slip": self.tier2_slip,
            "participation_limit": self.participation_limit,
        }

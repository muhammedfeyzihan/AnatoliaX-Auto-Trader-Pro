"""
portfolio_orchestrator.py — Dynamic capital allocation across strategies.
K232: PortfolioOrchestrator.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Allocation:
    strategy: str = ""
    weight: float = 0.0
    capital: float = 0.0
    expected_return: float = 0.0
    risk_contrib: float = 0.0


class PortfolioOrchestrator:
    """
    Dinamik sermaye dagilimi: stratejiler arasi agirlik atama.
    Risk-parity + momentum boost.
    """

    def __init__(
        self,
        total_capital: float = 100_000.0,
        min_weight: float = 0.05,
        max_weight: float = 0.50,
        rebalance_threshold: float = 0.05,
    ):
        self.total_capital = total_capital
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.rebalance_threshold = rebalance_threshold
        self._allocations: Dict[str, Allocation] = {}
        self._history: List[Dict] = []

    def allocate(self, strategies: List[Dict]) -> Dict[str, Allocation]:
        """
        strategies: [{"name": str, "sharpe": float, "recent_pnl": float, "volatility": float}]
        """
        if not strategies:
            return {}

        # Momentum score: sharpe * recent_pnl / vol
        scores = []
        for s in strategies:
            vol = s.get("volatility", 0.01)
            score = s.get("sharpe", 0) * max(0, s.get("recent_pnl", 0)) / max(vol, 1e-9)
            scores.append(max(score, 0))

        total_score = sum(scores) if sum(scores) > 0 else 1.0
        weights = [s / total_score for s in scores]

        # Clamp weights
        weights = [max(self.min_weight, min(self.max_weight, w)) for w in weights]
        # Renormalize only if there are multiple strategies and not all hit max cap
        total_w = sum(weights)
        if len(strategies) > 1 and total_w > 0:
            weights = [w / total_w for w in weights]

        allocs = {}
        for i, s in enumerate(strategies):
            alloc = Allocation(
                strategy=s["name"],
                weight=weights[i],
                capital=self.total_capital * weights[i],
                expected_return=s.get("sharpe", 0) * weights[i],
                risk_contrib=s.get("volatility", 0) * weights[i],
            )
            allocs[s["name"]] = alloc

        self._allocations = allocs
        self._history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "allocations": {k: v.weight for k, v in allocs.items()},
        })
        return allocs

    def rebalance_needed(self, new_allocations: Dict[str, Allocation]) -> bool:
        for name, alloc in new_allocations.items():
            old = self._allocations.get(name)
            if not old or abs(old.weight - alloc.weight) > self.rebalance_threshold:
                return True
        return False

    def get_allocations(self) -> Dict[str, Allocation]:
        return self._allocations.copy()

    def get_summary(self) -> Dict:
        if not self._allocations:
            return {}
        weights = [a.weight for a in self._allocations.values()]
        returns = [a.expected_return for a in self._allocations.values()]
        risks = [a.risk_contrib for a in self._allocations.values()]
        return {
            "strategies": len(self._allocations),
            "total_capital": self.total_capital,
            "avg_weight": np.mean(weights),
            "max_weight": max(weights),
            "total_expected_return": sum(returns),
            "total_risk_contrib": sum(risks),
        }

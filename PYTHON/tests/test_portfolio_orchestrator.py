"""
test_portfolio_orchestrator.py — Tests for PortfolioOrchestrator (K232)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategy.portfolio_orchestrator import PortfolioOrchestrator


class TestPortfolioOrchestrator:
    def test_allocate_basic(self):
        orch = PortfolioOrchestrator(total_capital=100000)
        strategies = [
            {"name": "trend", "sharpe": 1.5, "recent_pnl": 5000, "volatility": 0.15},
            {"name": "mean_rev", "sharpe": 0.8, "recent_pnl": 2000, "volatility": 0.10},
        ]
        allocs = orch.allocate(strategies)
        assert "trend" in allocs
        assert "mean_rev" in allocs
        assert allocs["trend"].capital > allocs["mean_rev"].capital

    def test_weight_clamping(self):
        orch = PortfolioOrchestrator(total_capital=100000, max_weight=0.30)
        strategies = [
            {"name": "a", "sharpe": 10, "recent_pnl": 50000, "volatility": 0.01},
        ]
        allocs = orch.allocate(strategies)
        assert allocs["a"].weight <= 0.30

    def test_rebalance_needed(self):
        orch = PortfolioOrchestrator(total_capital=100000, rebalance_threshold=0.01, max_weight=1.0)
        strategies = [
            {"name": "a", "sharpe": 1, "recent_pnl": 1000, "volatility": 0.1},
            {"name": "b", "sharpe": 1, "recent_pnl": 1000, "volatility": 0.1},
        ]
        old = orch.allocate(strategies)
        new = orch.allocate([
            {"name": "a", "sharpe": 10, "recent_pnl": 10000, "volatility": 0.1},
            {"name": "b", "sharpe": 1, "recent_pnl": 1000, "volatility": 0.1},
        ])
        # Compare old allocations against new
        for name, alloc in new.items():
            if name in old and abs(old[name].weight - alloc.weight) > 0.01:
                assert True
                return
        assert False, "No rebalance detected"

    def test_empty_strategies(self):
        orch = PortfolioOrchestrator()
        assert orch.allocate([]) == {}

    def test_summary(self):
        orch = PortfolioOrchestrator(total_capital=100000)
        orch.allocate([
            {"name": "a", "sharpe": 1, "recent_pnl": 1000, "volatility": 0.1},
            {"name": "b", "sharpe": 1, "recent_pnl": 1000, "volatility": 0.1},
        ])
        summary = orch.get_summary()
        assert summary["strategies"] == 2
        assert summary["total_capital"] == 100000

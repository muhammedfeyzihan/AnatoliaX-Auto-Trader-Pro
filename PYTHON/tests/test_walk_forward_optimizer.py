"""
test_walk_forward_optimizer.py — Tests for WalkForwardOptimizer (K225)
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.walk_forward_optimizer import WalkForwardOptimizer


def dummy_backtest(params, df):
    close = df["close"].values
    pnl = (close[-1] - close[0]) * params.get("multiplier", 1)
    returns = np.diff(close) / close[:-1]
    sharpe = returns.mean() / (returns.std() + 1e-9) * np.sqrt(len(returns))
    return {"sharpe": sharpe, "pnl": pnl}


class TestWalkForwardOptimizer:
    def test_optimize_basic(self):
        df = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(200) * 0.5),
            "high": 101 + np.cumsum(np.random.randn(200) * 0.5),
            "low": 99 + np.cumsum(np.random.randn(200) * 0.5),
        })
        wfo = WalkForwardOptimizer(
            param_grid={"multiplier": [1, 2, 3]},
            train_size=50,
            test_size=20,
        )
        results = wfo.optimize(df, dummy_backtest)
        assert len(results) > 0

    def test_approval_logic(self):
        df = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(100) * 0.1 + 0.05),
            "high": 101 + np.cumsum(np.random.randn(100) * 0.1 + 0.05),
            "low": 99 + np.cumsum(np.random.randn(100) * 0.1 + 0.05),
        })
        wfo = WalkForwardOptimizer(
            param_grid={"multiplier": [1]},
            train_size=50,
            test_size=30,
            min_sharpe=-10,
            max_degradation=1.0,
        )
        results = wfo.optimize(df, dummy_backtest)
        assert len(results) > 0
        assert isinstance(results[0].approved, bool)

    def test_best_params(self):
        df = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(100) * 0.1),
            "high": 101 + np.cumsum(np.random.randn(100) * 0.1),
            "low": 99 + np.cumsum(np.random.randn(100) * 0.1),
        })
        wfo = WalkForwardOptimizer(
            param_grid={"multiplier": [1, 2]},
            train_size=50,
            test_size=30,
        )
        wfo.optimize(df, dummy_backtest)
        best = wfo.get_best_params()
        assert best is not None
        assert "multiplier" in best

    def test_summary(self):
        df = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(100) * 0.1),
            "high": 101 + np.cumsum(np.random.randn(100) * 0.1),
            "low": 99 + np.cumsum(np.random.randn(100) * 0.1),
        })
        wfo = WalkForwardOptimizer(
            param_grid={"multiplier": [1]},
            train_size=50,
            test_size=30,
        )
        wfo.optimize(df, dummy_backtest)
        summary = wfo.get_summary()
        assert "windows" in summary
        assert summary["windows"] >= 1

    def test_short_data(self):
        df = pd.DataFrame({
            "close": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
        })
        wfo = WalkForwardOptimizer(
            param_grid={"multiplier": [1]},
            train_size=50,
            test_size=30,
        )
        results = wfo.optimize(df, dummy_backtest)
        assert len(results) == 0

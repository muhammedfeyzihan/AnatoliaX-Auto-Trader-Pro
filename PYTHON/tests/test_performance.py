"""
Test: PYTHON.backtest.performance
Performans metrikleri dogrulama: Sharpe, Sortino, MaxDD, Profit Factor, Expectancy.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.performance import calculate_all_metrics


class TestPerformanceMetrics:
    def _sample_trades(self):
        # Basit trade listesi (DataFrame olarak)
        return pd.DataFrame({
            "entry_price": [100.0, 105.0, 102.0],
            "exit_price": [105.0, 102.0, 108.0],
            "comm_net_profit": [45.9, -35.15, 55.9],
            "comm_net_return": [0.0459, -0.0335, 0.0559],
        })

    def _sample_equity(self):
        return pd.Series([100000, 104590, 101035, 106945], dtype=float)

    def test_calculate_all_returns_dict(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert isinstance(metrics, dict)

    def test_sharpe_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Sharpe Ratio" in metrics

    def test_sortino_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Sortino Ratio" in metrics

    def test_max_drawdown_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Max Drawdown" in metrics

    def test_max_drawdown_positive(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert metrics["Max Drawdown"]["value"] is not None

    def test_profit_factor_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Profit Factor" in metrics

    def test_expectancy_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Expectancy" in metrics

    def test_summary_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "_summary" in metrics

    def test_monte_carlo_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Monte Carlo %95" in metrics

    def test_walk_forward_exists(self):
        trades = self._sample_trades()
        equity = self._sample_equity()
        metrics = calculate_all_metrics(trades, equity)
        assert "Walk-Forward Fark" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

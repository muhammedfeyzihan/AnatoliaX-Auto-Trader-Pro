"""
test_trade_analytics.py — Trade Analytics Tests
"""

import pytest
import pandas as pd
import numpy as np
from analytics.trade_analytics import TradeAnalytics


class TestTradeAnalytics:
    def test_streak_analysis(self):
        ta = TradeAnalytics()
        outcomes = [10, 10, -5, -5, -5, 10, 10, 10, 10, -2]
        result = ta.streak_analysis(outcomes)
        assert result["max_win_streak"] == 4
        assert result["max_loss_streak"] == 3
        assert result["win_rate"] == 0.6

    def test_streak_analysis_empty(self):
        ta = TradeAnalytics()
        result = ta.streak_analysis([])
        assert result["max_win_streak"] == 0
        assert result["max_loss_streak"] == 0

    def test_calmar_ratio(self):
        ta = TradeAnalytics()
        equity = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5 + 0.1))
        calmar = ta.calmar_ratio(equity)
        assert calmar >= 0

    def test_calmar_ratio_insufficient(self):
        ta = TradeAnalytics()
        equity = pd.Series([100])
        assert ta.calmar_ratio(equity) == 0.0

    def test_omega_ratio(self):
        ta = TradeAnalytics()
        returns = pd.Series([0.02, -0.01, 0.03, -0.005, 0.01])
        omega = ta.omega_ratio(returns, threshold=0.0)
        assert omega > 0

    def test_omega_ratio_all_positive(self):
        ta = TradeAnalytics()
        returns = pd.Series([0.01, 0.02, 0.03])
        omega = ta.omega_ratio(returns, threshold=0.0)
        assert omega == float("inf")

    def test_omega_ratio_all_negative(self):
        ta = TradeAnalytics()
        returns = pd.Series([-0.01, -0.02, -0.03])
        omega = ta.omega_ratio(returns, threshold=0.0)
        assert omega == 0.0

    def test_trade_attribution(self):
        ta = TradeAnalytics()
        trades = pd.DataFrame({
            "net_pnl": [100, -50, 80, -30, 120],
            "signal_type": ["trend", "mean_rev", "trend", "mean_rev", "trend"],
            "entry_price": [100, 100, 100, 100, 100],
            "size": [1, 1, 1, 1, 1],
        })
        attr = ta.trade_attribution(trades, signal_type_col="signal_type")
        assert "trend" in attr
        assert "mean_rev" in attr
        assert attr["trend"]["count"] == 3

    def test_trade_attribution_no_col(self):
        ta = TradeAnalytics()
        trades = pd.DataFrame({"net_pnl": [100]})
        attr = ta.trade_attribution(trades)
        assert attr == {}

    def test_analyze(self):
        ta = TradeAnalytics()
        trades = pd.DataFrame({
            "net_pnl": [100, -50, 80, -30, 120],
            "entry_price": [100, 100, 100, 100, 100],
            "size": [1, 1, 1, 1, 1],
        })
        equity = pd.Series(100 + np.cumsum(trades["net_pnl"]))
        result = ta.analyze(trades, equity)
        assert result["total_trades"] == 5
        assert result["profit_factor"] > 0
        assert "streaks" in result
        assert "calmar_ratio" in result
        assert "omega_ratio" in result

    def test_analyze_empty(self):
        ta = TradeAnalytics()
        result = ta.analyze(pd.DataFrame())
        assert "error" in result

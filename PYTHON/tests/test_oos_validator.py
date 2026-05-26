"""
test_oos_validator.py — OOS Validator Tests
"""

import pytest
import pandas as pd
import numpy as np
from backtest.oos_validator import OOSValidator


def _mock_strategy(df):
    """Mock strategy that returns a dict with 'sharpe'."""
    returns = df["close"].pct_change().dropna()
    if returns.std() == 0:
        return {"sharpe": 0.0}
    sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252) + 1e-12)
    return {"sharpe": sharpe}


class TestOOSValidator:
    def test_walk_forward_basic(self):
        dates = pd.date_range("2020-01-01", periods=200, freq="D")
        df = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(200) * 0.5),
            "high": 101 + np.cumsum(np.random.randn(200) * 0.5),
            "low": 99 + np.cumsum(np.random.randn(200) * 0.5),
        }, index=dates)
        validator = OOSValidator()
        results = validator.walk_forward(df, _mock_strategy, train_window=126, test_window=42, step=42)
        assert len(results) >= 1
        assert "is" in results[0]
        assert "oos" in results[0]

    def test_walk_forward_insufficient_data(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        validator = OOSValidator()
        results = validator.walk_forward(df, _mock_strategy, train_window=10, test_window=5, step=5)
        assert len(results) == 0

    def test_regime_split_backtest(self):
        dates = pd.date_range("2020-01-01", periods=300, freq="D")
        trend = np.cumsum(np.random.randn(300) * 0.3 + 0.1)
        df = pd.DataFrame({
            "close": 100 + trend,
            "high": 101 + trend,
            "low": 99 + trend,
        }, index=dates)
        validator = OOSValidator()
        results = validator.regime_split_backtest(df, _mock_strategy)
        assert "bull" in results or "bear" in results or "sideways" in results

    def test_sharpe_inflation_detected(self):
        validator = OOSValidator()
        is_results = [{"sharpe": 3.0}]
        oos_results = [{"sharpe": 1.0}]
        result = validator.sharpe_inflation_test(is_results, oos_results)
        assert result["overfitting"] is True
        assert result["ratio"] == pytest.approx(3.0, rel=1e-2)

    def test_sharpe_inflation_not_detected(self):
        validator = OOSValidator()
        is_results = [{"sharpe": 1.5}]
        oos_results = [{"sharpe": 1.2}]
        result = validator.sharpe_inflation_test(is_results, oos_results)
        assert result["overfitting"] is False

    def test_sharpe_inflation_empty(self):
        validator = OOSValidator()
        result = validator.sharpe_inflation_test([], [])
        assert result["overfitting"] is False
        assert result["ratio"] is None

    def test_whites_reality_check_significant(self):
        validator = OOSValidator()
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = validator.whites_reality_check(returns, n_bootstrap=500)
        assert "p_value" in result
        assert "significant" in result

    def test_whites_reality_check_insufficient(self):
        validator = OOSValidator()
        returns = pd.Series([0.01, -0.01])
        result = validator.whites_reality_check(returns)
        assert result["p_value"] is None

    def test_sharpe_calculation(self):
        validator = OOSValidator()
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        sharpe = validator._sharpe(returns)
        assert isinstance(sharpe, float)

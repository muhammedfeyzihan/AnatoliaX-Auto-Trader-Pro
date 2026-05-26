"""
Test: PYTHON.risk.portfolio_optimizer
Markowitz optimizasyon, kisitlar, efficient frontier.
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.portfolio_optimizer import PortfolioOptimizer


class TestPortfolioOptimizer:
    @pytest.fixture
    def sample_returns(self):
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=60)
        data = {
            "THYAO": np.random.normal(0.001, 0.02, 60),
            "GARAN": np.random.normal(0.0008, 0.018, 60),
            "ASELS": np.random.normal(0.0005, 0.025, 60),
        }
        return pd.DataFrame(data, index=dates)

    def test_init_defaults(self):
        opt = PortfolioOptimizer()
        assert opt.max_weight == 0.02
        assert opt.max_stocks == 5

    def test_init_custom(self):
        opt = PortfolioOptimizer(max_weight_pct=5.0, max_stocks=3)
        assert opt.max_weight == 0.05
        assert opt.max_stocks == 3

    def test_fetch_returns_mock(self, sample_returns):
        opt = PortfolioOptimizer()
        with patch.object(opt.feed, "fetch", return_value=pd.DataFrame({"close": [100.0, 101.0, 102.0]})):
            df = opt._fetch_returns(["THYAO", "GARAN"])
        assert not df.empty
        assert "THYAO" in df.columns

    def test_optimize_insufficient_symbols(self):
        opt = PortfolioOptimizer()
        result = opt.optimize(symbols=["THYAO"])
        assert "error" in result
        assert result["weights"] == {}

    def test_optimize_empty_data(self):
        opt = PortfolioOptimizer()
        with patch.object(opt.feed, "fetch", return_value=pd.DataFrame()):
            result = opt.optimize(symbols=["THYAO", "GARAN"])
        assert "error" in result

    def test_max_sharpe_weights_sum_to_one(self, sample_returns):
        opt = PortfolioOptimizer()
        mean_ret = sample_returns.mean() * 252
        cov = sample_returns.cov() * 252
        weights, sharpe, p_ret, p_vol = opt._max_sharpe_portfolio(mean_ret, cov, 0.10)
        assert np.isclose(np.sum(weights), 1.0, atol=0.01)
        assert sharpe is not None
        assert p_vol >= 0

    def test_apply_constraints_max_stocks(self):
        opt = PortfolioOptimizer(max_stocks=3)
        raw = {"A": 0.3, "B": 0.25, "C": 0.2, "D": 0.15, "E": 0.1}
        out = opt._apply_constraints(raw)
        assert len(out) <= 3

    def test_apply_constraints_max_weight(self):
        opt = PortfolioOptimizer(max_weight_pct=2.0)
        raw = {"A": 0.5, "B": 0.3, "C": 0.2}
        out = opt._apply_constraints(raw)
        assert all(v <= 0.02 + 1e-6 for v in out.values())

    def test_apply_constraints_no_normalization(self):
        opt = PortfolioOptimizer(max_weight_pct=2.0, max_stocks=5)
        raw = {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}
        out = opt._apply_constraints(raw)
        total = sum(out.values())
        assert total <= 0.10 + 1e-6  # 5 hisse x %2 = max %10

    def test_efficient_frontier_length(self, sample_returns):
        opt = PortfolioOptimizer(max_weight_pct=50.0)  # 3 hisse ile feasible olmasi icin
        mean_ret = sample_returns.mean() * 252
        cov = sample_returns.cov() * 252
        frontier = opt._efficient_frontier(mean_ret, cov, n_points=10)
        assert len(frontier) > 0
        for vol, ret in frontier:
            assert vol >= 0
            assert isinstance(ret, float)

    def test_optimize_result_keys(self, sample_returns):
        opt = PortfolioOptimizer()
        with patch.object(opt, "_fetch_returns", return_value=sample_returns):
            result = opt.optimize(symbols=["THYAO", "GARAN", "ASELS"])
        assert "weights" in result
        assert "sharpe" in result
        assert "expected_return" in result
        assert "volatility" in result
        assert "frontier" in result
        assert "method" in result

    def test_optimize_fallback_on_exception(self, sample_returns):
        opt = PortfolioOptimizer()
        with patch.object(opt, "_fetch_returns", return_value=sample_returns):
            with patch.object(opt, "_max_sharpe_portfolio", side_effect=Exception("fail")):
                result = opt.optimize(symbols=["THYAO", "GARAN", "ASELS"])
        assert "weights" in result
        assert result["method"] == "markowitz"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

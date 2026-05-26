"""
test_ensemble_optimizer.py — Ensemble Optimizer Tests
"""

import pytest
import pandas as pd
import numpy as np
from strategy.ensemble_optimizer import EnsembleOptimizer


class TestEnsembleOptimizer:
    def test_correlation_matrix(self):
        opt = EnsembleOptimizer()
        returns = pd.DataFrame({
            "strat_a": np.random.normal(0.001, 0.02, 100),
            "strat_b": np.random.normal(0.001, 0.02, 100),
        })
        corr = opt.correlation_matrix(returns)
        assert corr.shape == (2, 2)
        assert corr.iloc[0, 0] == 1.0

    def test_check_correlation_alert(self):
        opt = EnsembleOptimizer()
        returns = pd.DataFrame({
            "strat_a": np.random.normal(0.001, 0.02, 100),
            "strat_b": np.random.normal(0.001, 0.02, 100),
        })
        alerts = opt.check_correlation_alert(returns, threshold=0.99)
        # Very unlikely to have >0.99 correlation on random data
        assert len(alerts) == 0

    def test_check_correlation_alert_triggered(self):
        opt = EnsembleOptimizer()
        base = np.random.normal(0.001, 0.02, 100)
        returns = pd.DataFrame({
            "strat_a": base,
            "strat_b": base * 1.01,  # Highly correlated
        })
        alerts = opt.check_correlation_alert(returns, threshold=0.80)
        assert len(alerts) >= 1
        assert alerts[0]["correlation"] > 0.80

    def test_regime_weights_bull(self):
        opt = EnsembleOptimizer()
        weights = opt.regime_weights("bull", ["trend_following", "mean_reversion", "hedge"])
        assert weights["trend_following"] > weights["mean_reversion"]
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_regime_weights_bear(self):
        opt = EnsembleOptimizer()
        weights = opt.regime_weights("bear", ["trend_following", "mean_reversion", "hedge"])
        assert weights["trend_following"] == 0.0
        assert weights["hedge"] > 0

    def test_regime_weights_unknown_strategy(self):
        opt = EnsembleOptimizer()
        weights = opt.regime_weights("bull", ["unknown_strat"])
        assert "unknown_strat" in weights
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_cvar_optimize_basic(self):
        opt = EnsembleOptimizer(max_weight=1.0)
        returns = pd.DataFrame({
            "low_vol": np.random.normal(0.0005, 0.01, 100),
            "high_vol": np.random.normal(0.001, 0.03, 100),
        })
        result = opt.cvar_optimize(returns, confidence=0.95)
        assert "weights" in result
        assert "cvar" in result
        assert len(result["weights"]) == 2

    def test_cvar_optimize_insufficient(self):
        opt = EnsembleOptimizer()
        returns = pd.DataFrame({"only_one": [0.01, -0.01]})
        result = opt.cvar_optimize(returns)
        assert "error" in result

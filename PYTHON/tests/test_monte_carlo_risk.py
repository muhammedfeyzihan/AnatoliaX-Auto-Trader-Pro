"""
test_monte_carlo_risk.py — Tests for MonteCarloRiskWrapper (K233)
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.monte_carlo_risk import MonteCarloRiskWrapper


class TestMonteCarloRiskWrapper:
    def test_analyze_basic(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        mc = MonteCarloRiskWrapper(n_simulations=1000)
        result = mc.analyze(returns, initial_capital=100000)
        assert result.simulations == 1000
        assert result.var_95 <= 0  # VaR is negative or zero
        assert 0 <= result.prob_positive <= 1

    def test_short_series(self):
        returns = pd.Series([0.01, -0.01])
        mc = MonteCarloRiskWrapper(n_simulations=1000)
        result = mc.analyze(returns)
        assert result.simulations == 0

    def test_positive_bias(self):
        returns = pd.Series(np.random.normal(0.01, 0.01, 200))
        mc = MonteCarloRiskWrapper(n_simulations=500)
        result = mc.analyze(returns)
        assert result.prob_positive > 0.5

    def test_negative_bias(self):
        returns = pd.Series(np.random.normal(-0.01, 0.01, 200))
        mc = MonteCarloRiskWrapper(n_simulations=500)
        result = mc.analyze(returns)
        assert result.prob_positive < 0.5

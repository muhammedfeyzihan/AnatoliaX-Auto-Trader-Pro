"""
monte_carlo_risk.py — Probabilistic risk analysis wrapper for Monte Carlo.
K233: MonteCarloProbabilisticWrapper.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MCRiskResult:
    var_95: float = 0.0
    cvar_95: float = 0.0
    prob_positive: float = 0.0
    prob_breach: float = 0.0
    expected_max_dd: float = 0.0
    worst_case_dd: float = 0.0
    simulations: int = 0


class MonteCarloRiskWrapper:
    """
    Monte Carlo simulasyonu uzerinden olasiliksal risk analizi.
    VaR, CVaR, pozitif getiri olasiligi, DD dagilimi.
    """

    def __init__(self, n_simulations: int = 10_000, confidence: float = 0.95):
        self.n_simulations = n_simulations
        self.confidence = confidence

    def analyze(self, returns: pd.Series, initial_capital: float = 100_000) -> MCRiskResult:
        """Tarihsel getiri dagilimindan MC simulasyonu uret."""
        if len(returns) < 10:
            return MCRiskResult(simulations=0)

        mu = returns.mean()
        sigma = returns.std()
        n_days = len(returns)

        # Bootstrap: sample with replacement
        simulated = np.random.choice(returns.values, size=(self.n_simulations, n_days), replace=True)
        cumulative = np.cumprod(1 + simulated, axis=1) * initial_capital
        final_pnl = cumulative[:, -1] - initial_capital
        max_dd = self._max_drawdowns(cumulative)

        alpha = 1 - self.confidence
        var = np.percentile(final_pnl, alpha * 100)
        cvar = final_pnl[final_pnl <= var].mean() if any(final_pnl <= var) else var
        prob_positive = np.mean(final_pnl > 0)
        prob_breach = np.mean(max_dd > 0.20)  # %20 DD breach

        return MCRiskResult(
            var_95=var,
            cvar_95=cvar,
            prob_positive=prob_positive,
            prob_breach=prob_breach,
            expected_max_dd=np.mean(max_dd),
            worst_case_dd=np.percentile(max_dd, 99),
            simulations=self.n_simulations,
        )

    def _max_drawdowns(self, equity_curves: np.ndarray) -> np.ndarray:
        peaks = np.maximum.accumulate(equity_curves, axis=1)
        dd = (peaks - equity_curves) / peaks
        return dd.max(axis=1)

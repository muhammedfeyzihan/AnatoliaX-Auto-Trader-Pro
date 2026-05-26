"""
ensemble_optimizer.py — Multi-Strategy Ensemble Optimizer
K171-K174: CVaR, correlation matrix, regime-based strategy switching.
"""

import numpy as np
import pandas as pd
from typing import Dict, List


class EnsembleOptimizer:
    """
    Birden fazla stratejiyi optimal ağırlıklandıran motor.
    """

    def __init__(self, max_weight: float = 0.40, min_weight: float = 0.0):
        self.max_weight = max_weight
        self.min_weight = min_weight

    # ── CVaR Optimization (K171) ─────────────────────────

    def cvar_optimize(
        self,
        returns_df: pd.DataFrame,
        confidence: float = 0.95,
    ) -> Dict:
        """
        Conditional Value at Risk minimize eden ağırlıklar.
        """
        try:
            import scipy.optimize as sco
        except ImportError:
            return {"error": "scipy required", "weights": {}}

        if returns_df.empty or len(returns_df.columns) < 2:
            return {"error": "Need at least 2 strategies", "weights": {}}

        n = len(returns_df.columns)
        mean_returns = returns_df.mean().values
        returns_matrix = returns_df.values

        def _cvar(weights):
            portfolio_returns = returns_matrix @ weights
            var_threshold = np.percentile(portfolio_returns, (1 - confidence) * 100)
            cvar = -np.mean(portfolio_returns[portfolio_returns <= var_threshold])
            return cvar

        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n))
        init_guess = np.ones(n) / n

        result = sco.minimize(
            _cvar,
            init_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            weights = {col: float(w) for col, w in zip(returns_df.columns, result.x)}
            cvar_value = float(_cvar(result.x))
            return {
                "weights": weights,
                "cvar": round(cvar_value, 6),
                "method": "cvar",
            }
        return {"error": "Optimization failed", "weights": {}}

    # ── Strategy Correlation Matrix (K172) ───────────────

    def correlation_matrix(self, strategies_returns: pd.DataFrame) -> pd.DataFrame:
        """
        Stratejiler arası korelasyon matrisi.
        """
        return strategies_returns.corr()

    def check_correlation_alert(
        self,
        strategies_returns: pd.DataFrame,
        threshold: float = 0.80,
    ) -> List[dict]:
        """
        Korelasyon > threshold olan strateji çiftlerini döner.
        """
        corr = self.correlation_matrix(strategies_returns)
        alerts = []
        cols = corr.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = corr.iloc[i, j]
                if val >= threshold:
                    alerts.append({
                        "strategy_a": cols[i],
                        "strategy_b": cols[j],
                        "correlation": round(val, 4),
                    })
        return alerts

    # ── Regime-Based Weights (K173-K174) ─────────────────

    REGIME_STRATEGY_MAP = {
        "bull": {
            "trend_following": 0.50,
            "momentum": 0.30,
            "breakout": 0.20,
            "mean_reversion": 0.0,
            "hedge": 0.0,
        },
        "bear": {
            "trend_following": 0.0,
            "momentum": 0.0,
            "breakout": 0.0,
            "mean_reversion": 0.50,
            "hedge": 0.50,
        },
        "sideways": {
            "trend_following": 0.10,
            "momentum": 0.10,
            "breakout": 0.10,
            "mean_reversion": 0.50,
            "hedge": 0.20,
        },
    }

    def regime_weights(
        self,
        regime: str,
        strategy_pool: List[str],
    ) -> Dict[str, float]:
        """
        Piyasa rejimine göre strateji ağırlıkları.
        """
        mapping = self.REGIME_STRATEGY_MAP.get(regime, {})
        weights = {}
        total = 0.0
        for strat in strategy_pool:
            w = mapping.get(strat, 0.05)
            weights[strat] = w
            total += w
        # Normalize
        if total > 0:
            weights = {k: round(v / total, 4) for k, v in weights.items()}
        else:
            n = len(strategy_pool)
            weights = {s: 1.0 / n for s in strategy_pool}
        return weights

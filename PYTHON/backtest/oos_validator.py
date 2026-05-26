"""
oos_validator.py — Out-of-Sample Test Protocol
K159-K162: Walk-forward, regime-specific backtest, Sharpe inflation detection.
"""

import numpy as np
import pandas as pd
from typing import Callable, List, Dict, Optional
from datetime import timedelta


class OOSValidator:
    """
    Overfitting'i önlemek için out-of-sample validasyon protokolü.
    """

    def __init__(self, risk_free_rate: float = 0.10):
        self.risk_free_rate = risk_free_rate

    # ── Walk-Forward Analysis (K159) ─────────────────────

    def walk_forward(
        self,
        df: pd.DataFrame,
        strategy_fn: Callable,
        train_window: int = 126,   # ~6 ay (günlük)
        test_window: int = 42,     # ~2 ay
        step: int = 42,
    ) -> List[dict]:
        """
        Rolling walk-forward analizi.
        Returns: her adım için IS ve OOS metrikler listesi.
        """
        results = []
        n = len(df)
        for start in range(0, n - train_window - test_window + 1, step):
            train_df = df.iloc[start : start + train_window].copy()
            test_df = df.iloc[start + train_window : start + train_window + test_window].copy()

            is_result = strategy_fn(train_df)
            oos_result = strategy_fn(test_df)

            results.append({
                "window": start // step,
                "is": is_result,
                "oos": oos_result,
            })
        return results

    # ── Rejim Bazlı Backtest (K160) ──────────────────────

    def regime_split_backtest(
        self,
        df: pd.DataFrame,
        strategy_fn: Callable,
    ) -> Dict[str, dict]:
        """
        Bull / Bear / Sideways rejimlerine göre ayrı backtest.
        Rejim tanımları:
        - Bull: ADX > 25 and SMA50 > SMA200
        - Bear: ADX > 25 and SMA50 < SMA200
        - Sideways: ADX <= 20
        """
        df = df.copy()
        df["SMA50"] = df["close"].rolling(window=50, min_periods=1).mean()
        df["SMA200"] = df["close"].rolling(window=200, min_periods=1).mean()
        # Simplified ADX proxy using ATR-like volatility
        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14, min_periods=1).mean()
        df["ADX"] = (atr / df["close"]).rolling(window=14, min_periods=1).mean() * 100

        regimes = {
            "bull": df[(df["ADX"] > 25) & (df["SMA50"] > df["SMA200"])],
            "bear": df[(df["ADX"] > 25) & (df["SMA50"] < df["SMA200"])],
            "sideways": df[df["ADX"] <= 20],
        }

        results = {}
        for name, subset in regimes.items():
            if len(subset) > 10:
                results[name] = strategy_fn(subset)
            else:
                results[name] = {"error": "Insufficient data", "sharpe": None}
        return results

    # ── Sharpe Inflation / Overfitting (K161) ─────────────

    def sharpe_inflation_test(
        self,
        is_results: List[dict],
        oos_results: List[dict],
    ) -> dict:
        """
        In-sample Sharpe / OOS Sharpe ratio > 2.0 → overfitting flag.
        """
        is_sharpes = [r.get("sharpe", 0.0) for r in is_results if r.get("sharpe") is not None]
        oos_sharpes = [r.get("sharpe", 0.0) for r in oos_results if r.get("sharpe") is not None]

        if not is_sharpes or not oos_sharpes:
            return {"overfitting": False, "ratio": None, "reason": "Insufficient results"}

        avg_is = np.mean(is_sharpes)
        avg_oos = np.mean(oos_sharpes)
        ratio = avg_is / (avg_oos + 1e-8)
        flag = bool(ratio > 2.0 and avg_oos > 0)

        return {
            "overfitting": flag,
            "ratio": round(ratio, 2),
            "avg_is_sharpe": round(avg_is, 2),
            "avg_oos_sharpe": round(avg_oos, 2),
            "reason": f"IS/OOS Sharpe ratio {ratio:.2f} > 2.0" if flag else f"Ratio OK: {ratio:.2f}",
        }

    # ── White's Reality Check (K162) ─────────────────────

    def whites_reality_check(
        self,
        returns: pd.Series,
        n_bootstrap: int = 1000,
    ) -> dict:
        """
        Bootstrap p-value ile White's Reality Check.
        Null hypothesis: strategy has no predictive power.
        """
        if len(returns) < 20:
            return {"p_value": None, "significant": False, "reason": "Insufficient data"}

        observed_sharpe = self._sharpe(returns)
        bootstrap_sharpes = []
        for _ in range(n_bootstrap):
            sampled = np.random.choice(returns.values, size=len(returns), replace=True)
            bootstrap_sharpes.append(self._sharpe(pd.Series(sampled)))

        p_value = np.mean([1 if bs >= observed_sharpe else 0 for bs in bootstrap_sharpes])
        significant = p_value < 0.05

        return {
            "p_value": round(p_value, 4),
            "significant": significant,
            "observed_sharpe": round(observed_sharpe, 4),
            "reason": "Significant predictive power" if significant else "No significant predictive power",
        }

    def _sharpe(self, returns: pd.Series) -> float:
        """Annualized Sharpe ratio."""
        if returns.std() == 0 or len(returns) == 0:
            return 0.0
        return (returns.mean() * 252 - self.risk_free_rate) / (returns.std() * np.sqrt(252) + 1e-12)

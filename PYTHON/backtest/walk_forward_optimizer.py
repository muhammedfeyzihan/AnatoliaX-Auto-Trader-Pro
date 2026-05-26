"""
walk_forward_optimizer.py — Rolling window parameter optimization.
K225: WalkForwardOptimizer.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
import numpy as np
import pandas as pd


@dataclass
class WFOptimResult:
    param_set: Dict[str, Any] = field(default_factory=dict)
    in_sample_sharpe: float = 0.0
    out_of_sample_sharpe: float = 0.0
    in_sample_pnl: float = 0.0
    out_of_sample_pnl: float = 0.0
    degradation: float = 0.0  # IS - OOS difference
    approved: bool = False


class WalkForwardOptimizer:
    """
    Walk-forward optimizasyon: parametreleri IS'de optimize et,
    OOS'de validasyon yap. Zorunlu IS/OOS split.
    """

    def __init__(
        self,
        param_grid: Dict[str, List],
        train_size: int = 100,
        test_size: int = 30,
        min_sharpe: float = 0.5,
        max_degradation: float = 0.20,
        objective: str = "sharpe",
    ):
        self.param_grid = param_grid
        self.train_size = train_size
        self.test_size = test_size
        self.min_sharpe = min_sharpe
        self.max_degradation = max_degradation
        self.objective = objective
        self._results: List[WFOptimResult] = []

    def optimize(self, df: pd.DataFrame, backtest_fn: Callable) -> List[WFOptimResult]:
        """
        df: price DataFrame (close, high, low)
        backtest_fn(params, train_df) -> {"sharpe": float, "pnl": float}
        """
        n = len(df)
        windows = []
        start = 0
        while start + self.train_size + self.test_size <= n:
            train = df.iloc[start:start + self.train_size]
            test = df.iloc[start + self.train_size:start + self.train_size + self.test_size]
            windows.append((train, test))
            start += self.test_size

        if not windows:
            return []

        all_results = []
        for train_df, test_df in windows:
            best = self._optimize_window(train_df, test_df, backtest_fn)
            if best:
                all_results.append(best)

        self._results = all_results
        return all_results

    def _optimize_window(self, train_df: pd.DataFrame, test_df: pd.DataFrame, backtest_fn: Callable) -> Optional[WFOptimResult]:
        from itertools import product
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        combinations = list(product(*values))

        best_is = -np.inf
        best_params = None
        best_is_metrics = None

        for combo in combinations:
            params = dict(zip(keys, combo))
            try:
                metrics = backtest_fn(params, train_df)
                score = metrics.get(self.objective, metrics.get("sharpe", 0))
                if score > best_is:
                    best_is = score
                    best_params = params
                    best_is_metrics = metrics
            except Exception:
                continue

        if not best_params:
            return None

        # OOS validation
        try:
            oos_metrics = backtest_fn(best_params, test_df)
        except Exception:
            return None

        is_sharpe = best_is_metrics.get("sharpe", 0)
        oos_sharpe = oos_metrics.get("sharpe", 0)
        is_pnl = best_is_metrics.get("pnl", 0)
        oos_pnl = oos_metrics.get("pnl", 0)
        degradation = abs(is_sharpe - oos_sharpe) / max(abs(is_sharpe), 1e-9)

        approved = bool(oos_sharpe >= self.min_sharpe and degradation <= self.max_degradation)
        return WFOptimResult(
            param_set=best_params,
            in_sample_sharpe=is_sharpe,
            out_of_sample_sharpe=oos_sharpe,
            in_sample_pnl=is_pnl,
            out_of_sample_pnl=oos_pnl,
            degradation=degradation,
            approved=approved,
        )

    def get_best_params(self) -> Optional[Dict]:
        if not self._results:
            return None
        approved = [r for r in self._results if r.approved]
        if approved:
            return max(approved, key=lambda x: x.out_of_sample_sharpe).param_set
        return self._results[0].param_set

    def get_summary(self) -> Dict:
        if not self._results:
            return {"windows": 0, "approved": 0}
        approved = sum(1 for r in self._results if r.approved)
        return {
            "windows": len(self._results),
            "approved": approved,
            "avg_degradation": np.mean([r.degradation for r in self._results]),
            "avg_oos_sharpe": np.mean([r.out_of_sample_sharpe for r in self._results]),
        }

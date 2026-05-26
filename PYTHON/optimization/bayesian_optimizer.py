"""
bayesian_optimizer.py — Bayesian Optimization for Strategy Parameters

Lightweight wrapper using scikit-optimize if available, falling back to
random search + grid refinement. Integrates with WalkForwardOptimizer.

Usage:
    from optimization.bayesian_optimizer import BayesianOptimizer
    opt = BayesianOptimizer(param_space={"ema_fast": (3, 50), "ema_slow": (10, 200)})
    best = opt.optimize(objective_fn, n_calls=50)
"""

import os
import sys
import time
import random
from pathlib import Path
from typing import Dict, Tuple, Callable, Optional, List, Any
from dataclasses import dataclass, field

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np

_SKOPT_AVAILABLE = False
try:
    from skopt import gp_minimize
    from skopt.space import Integer, Real, Categorical
    _SKOPT_AVAILABLE = True
except ImportError:
    pass


@dataclass
class BayesResult:
    best_params: Dict[str, Any]
    best_score: float
    n_calls: int
    n_random_starts: int
    duration_sec: float
    convergence: List[float] = field(default_factory=list)
    backend: str = "skopt"


class BayesianOptimizer:
    """
    Strategy parameter optimizer using Bayesian Optimization.
    Falls back to random search + local refinement if scikit-optimize unavailable.
    """

    def __init__(
        self,
        param_space: Dict[str, Tuple],
        maximize: bool = True,
        random_state: int = 42,
    ):
        self.param_space = param_space
        self.maximize = maximize
        self.random_state = random_state
        random.seed(random_state)
        np.random.seed(random_state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def optimize(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        n_calls: int = 50,
        n_random_starts: int = 10,
        callback: Optional[Callable[[int, Dict, float], None]] = None,
    ) -> BayesResult:
        """
        Run optimization.
        objective_fn: takes param dict, returns scalar score.
        """
        start = time.time()

        if _SKOPT_AVAILABLE and len(self.param_space) > 0:
            return self._optimize_skopt(objective_fn, n_calls, n_random_starts, callback)
        else:
            return self._optimize_fallback(objective_fn, n_calls, callback)

    # ------------------------------------------------------------------
    # scikit-optimize backend
    # ------------------------------------------------------------------
    def _optimize_skopt(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        n_calls: int,
        n_random_starts: int,
        callback: Optional[Callable],
    ) -> BayesResult:
        param_names = list(self.param_space.keys())
        space = self._build_skopt_space()
        convergence: List[float] = []
        best_score = -np.inf if self.maximize else np.inf
        best_params: Dict[str, Any] = {}

        def _wrapped(x):
            params = {name: val for name, val in zip(param_names, x)}
            score = objective_fn(params)
            # Track convergence
            current_best = max(score, best_score) if self.maximize else min(score, best_score)
            convergence.append(current_best)
            if callback:
                callback(len(convergence), params, score)
            # gp_minimize minimizes, so negate if maximizing
            return -score if self.maximize else score

        res = gp_minimize(
            _wrapped,
            space,
            n_calls=n_calls,
            n_random_starts=n_random_starts,
            random_state=self.random_state,
            verbose=False,
        )

        best_params = {name: val for name, val in zip(param_names, res.x)}
        best_score = -res.fun if self.maximize else res.fun

        return BayesResult(
            best_params=best_params,
            best_score=best_score,
            n_calls=n_calls,
            n_random_starts=n_random_starts,
            duration_sec=time.time() - start,
            convergence=convergence,
            backend="skopt",
        )

    def _build_skopt_space(self):
        from skopt.space import Integer, Real, Categorical
        space = []
        for name, bounds in self.param_space.items():
            if isinstance(bounds, tuple) and len(bounds) == 2:
                lo, hi = bounds
                if isinstance(lo, int) and isinstance(hi, int):
                    space.append(Integer(lo, hi, name=name))
                else:
                    space.append(Real(lo, hi, name=name))
            elif isinstance(bounds, list):
                space.append(Categorical(bounds, name=name))
            else:
                space.append(Real(bounds[0], bounds[1], name=name))
        return space

    # ------------------------------------------------------------------
    # Fallback: random search + local refinement
    # ------------------------------------------------------------------
    def _optimize_fallback(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        n_calls: int,
        callback: Optional[Callable],
    ) -> BayesResult:
        start = time.time()
        best_score = -np.inf if self.maximize else np.inf
        best_params: Dict[str, Any] = {}
        convergence: List[float] = []

        for i in range(n_calls):
            params = self._random_sample()
            score = objective_fn(params)
            improved = (self.maximize and score > best_score) or (not self.maximize and score < best_score)
            if improved:
                best_score = score
                best_params = params.copy()
            convergence.append(best_score)
            if callback:
                callback(i + 1, params, score)

        # Local refinement around best
        if best_params:
            refined = self._local_refinement(objective_fn, best_params, steps=5)
            if refined:
                r_score = objective_fn(refined)
                improved = (self.maximize and r_score > best_score) or (not self.maximize and r_score < best_score)
                if improved:
                    best_score = r_score
                    best_params = refined

        return BayesResult(
            best_params=best_params,
            best_score=best_score,
            n_calls=n_calls,
            n_random_starts=n_calls,
            duration_sec=time.time() - start,
            convergence=convergence,
            backend="fallback_random_search",
        )

    def _random_sample(self) -> Dict[str, Any]:
        params = {}
        for name, bounds in self.param_space.items():
            if isinstance(bounds, tuple) and len(bounds) == 2:
                lo, hi = bounds
                if isinstance(lo, int) and isinstance(hi, int):
                    params[name] = random.randint(lo, hi)
                else:
                    params[name] = random.uniform(lo, hi)
            elif isinstance(bounds, list):
                params[name] = random.choice(bounds)
            else:
                params[name] = random.choice(bounds)
        return params

    def _local_refinement(self, objective_fn, center: Dict[str, Any], steps: int = 5) -> Optional[Dict[str, Any]]:
        best = center.copy()
        best_score = objective_fn(best)
        for _ in range(steps):
            candidate = best.copy()
            # Perturb one random param
            key = random.choice(list(candidate.keys()))
            bounds = self.param_space[key]
            if isinstance(bounds, tuple) and len(bounds) == 2:
                lo, hi = bounds
                delta = (hi - lo) * 0.1
                if isinstance(lo, int):
                    candidate[key] = int(np.clip(candidate[key] + random.randint(-max(1, int(delta)), max(1, int(delta))), lo, hi))
                else:
                    candidate[key] = float(np.clip(candidate[key] + random.uniform(-delta, delta), lo, hi))
            score = objective_fn(candidate)
            improved = (self.maximize and score > best_score) or (not self.maximize and score < best_score)
            if improved:
                best_score = score
                best = candidate
        return best


if __name__ == "__main__":
    def demo_objective(params):
        ema_fast = params.get("ema_fast", 10)
        ema_slow = params.get("ema_slow", 20)
        # Fake objective: want fast < slow, maximize distance
        if ema_fast >= ema_slow:
            return -1000.0
        return -(ema_slow - ema_fast) ** 2 + 1000.0

    opt = BayesianOptimizer({"ema_fast": (3, 50), "ema_slow": (10, 200)})
    res = opt.optimize(demo_objective, n_calls=30, n_random_starts=10)
    print("Best:", res.best_params, "Score:", res.best_score, "Backend:", res.backend)

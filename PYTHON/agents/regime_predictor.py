"""
agents/regime_predictor.py — Regime Transition Prediction (Phase 4)
Module 13 from anatoliax_prompt_v6.txt

Features:
  - Predict P(regime_t+1 | regime_t, features_t)
  - Features: volatility_clustering (GARCH residuals), correlation_breakdown,
    volume_anomaly, options_skew, credit_spread
  - Model: Hidden Markov Model or LSTM with regime labels
  - Output: transition_probability_matrix P_ij, expected_time_horizon E[tau]
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


class RegimePredictor:
    """
    Regime transition prediction using a simplified HMM-like approach.
    """

    REGIMES = ["bull", "bear", "sideways", "volatile", "low_vol"]

    def __init__(self, n_regimes: int = 5):
        self.n_regimes = n_regimes
        self._transition_counts: Dict[Tuple[str, str], int] = {}
        self._regime_history: List[str] = []
        self._features: Dict[str, List[float]] = {
            "volatility_clustering": [],
            "correlation_breakdown": [],
            "volume_anomaly": [],
            "options_skew": [],
            "credit_spread": [],
        }

    def ingest(self, regime: str, features: Dict[str, float]):
        if self._regime_history:
            prev = self._regime_history[-1]
            self._transition_counts[(prev, regime)] = self._transition_counts.get((prev, regime), 0) + 1
        self._regime_history.append(regime)
        for k, v in features.items():
            if k in self._features:
                self._features[k].append(v)

    def transition_matrix(self) -> Dict[Tuple[str, str], float]:
        """P_ij = count(i->j) / sum(count(i->*))."""
        totals: Dict[str, int] = {}
        for (i, j), c in self._transition_counts.items():
            totals[i] = totals.get(i, 0) + c

        probs = {}
        for (i, j), c in self._transition_counts.items():
            probs[(i, j)] = c / totals[i] if totals[i] > 0 else 0.0
        return probs

    def predict_next(self, current_regime: str) -> Dict[str, float]:
        probs = self.transition_matrix()
        result = {}
        for r in self.REGIMES:
            result[r] = probs.get((current_regime, r), 0.0)
        # Normalize
        total = sum(result.values()) or 1.0
        for r in result:
            result[r] /= total
        return result

    def expected_horizon(self, regime: str) -> float:
        """Expected time in current regime before transition."""
        streak = 0
        for r in reversed(self._regime_history):
            if r == regime:
                streak += 1
            else:
                break
        return float(streak) if streak > 0 else 1.0

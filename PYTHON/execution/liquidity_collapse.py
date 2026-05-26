"""
execution/liquidity_collapse.py — Liquidity Collapse Intelligence (Phase 1)
Module 19 from anatoliax_prompt_v6.txt

Features:
  - Hidden collapse prediction via composite score:
    LCS = w1*IMB + w2*(dSpread/dt) + w3*(dVolume/dt) + w4*VPIN
  - Threshold: if LCS > theta and dLCS/dt > 0, predict collapse within T_pred minutes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import deque


@dataclass
class LiquidityCollapseConfig:
    w1: float = 0.3
    w2: float = 0.3
    w3: float = 0.2
    w4: float = 0.2
    theta: float = 0.7
    t_pred_minutes: float = 5.0
    window_size: int = 20


class LiquidityCollapseDetector:
    """
    Composite LCS score for predicting liquidity collapse.
    """

    def __init__(self, config: LiquidityCollapseConfig = None):
        self.config = config or LiquidityCollapseConfig()
        self._imbalance_history: deque = deque(maxlen=self.config.window_size)
        self._spread_history: deque = deque(maxlen=self.config.window_size)
        self._volume_history: deque = deque(maxlen=self.config.window_size)
        self._vpin_history: deque = deque(maxlen=self.config.window_size)
        self._lcs_history: deque = deque(maxlen=self.config.window_size)

    def ingest(
        self,
        imbalance: float,
        spread: float,
        volume: float,
        vpin: float,
    ):
        self._imbalance_history.append(imbalance)
        self._spread_history.append(spread)
        self._volume_history.append(volume)
        self._vpin_history.append(vpin)

    def _derivative(self, series: deque) -> float:
        if len(series) < 2:
            return 0.0
        return (series[-1] - series[-2]) / max(len(series) - 1, 1)

    def calculate_lcs(self) -> float:
        if len(self._imbalance_history) < self.config.window_size:
            return 0.0

        imb = self._imbalance_history[-1]
        d_spread = self._derivative(self._spread_history)
        d_volume = self._derivative(self._volume_history)
        vpin = self._vpin_history[-1]

        c = self.config
        lcs = c.w1 * imb + c.w2 * d_spread + c.w3 * d_volume + c.w4 * vpin
        self._lcs_history.append(lcs)
        return lcs

    def predict(self) -> Optional[Dict]:
        lcs = self.calculate_lcs()
        if len(self._lcs_history) < 2:
            return {"predicted": False, "lcs": lcs, "d_lcs": 0.0}

        d_lcs = self._derivative(self._lcs_history)
        if lcs > self.config.theta and d_lcs > 0:
            return {
                "predicted": True,
                "lcs": lcs,
                "d_lcs": d_lcs,
                "prediction_horizon_min": self.config.t_pred_minutes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {"predicted": False, "lcs": lcs, "d_lcs": d_lcs}

"""
execution/toxic_flow.py — Toxic Flow Detection (Phase 1)
Module 20 from anatoliax_prompt_v6.txt

Features:
  - Adverse Fill Quality: AFQ = (execution_price - midprice_5min_after) / spread
  - Liquidity Fade: LF = (midprice_1min_after - midprice_at_fill) / spread
  - Market Impact: MI = dP / (size / ADV)
  - Classification: toxic if AFQ < -0.3 AND LF < -0.2 AND MI > 2*sigma_MI
  - Adjust execution: if toxic_flow_probability > 0.7, switch to passive execution.
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque


@dataclass
class ToxicFlowConfig:
    afq_threshold: float = -0.3
    lf_threshold: float = -0.2
    mi_sigma_multiplier: float = 2.0
    toxic_probability_threshold: float = 0.7


class ToxicFlowDetector:
    """
    Detects toxic flow from execution quality metrics.
    """

    def __init__(self, config: ToxicFlowConfig = None):
        self.config = config or ToxicFlowConfig()
        self._mi_history: deque = deque(maxlen=100)

    def adverse_fill_quality(self, execution_price: float, midprice_5min_after: float, spread: float) -> float:
        if spread == 0:
            return 0.0
        return (execution_price - midprice_5min_after) / spread

    def liquidity_fade(self, midprice_1min_after: float, midprice_at_fill: float, spread: float) -> float:
        if spread == 0:
            return 0.0
        return (midprice_1min_after - midprice_at_fill) / spread

    def market_impact(self, price_change: float, size: float, adv: float) -> float:
        if adv == 0:
            return 0.0
        return price_change / (size / adv)

    def is_toxic(
        self,
        execution_price: float,
        midprice_5min_after: float,
        midprice_1min_after: float,
        midprice_at_fill: float,
        price_change: float,
        size: float,
        spread: float,
        adv: float,
    ) -> Dict:
        afq = self.adverse_fill_quality(execution_price, midprice_5min_after, spread)
        lf = self.liquidity_fade(midprice_1min_after, midprice_at_fill, spread)
        mi = self.market_impact(price_change, size, adv)
        self._mi_history.append(mi)

        mi_std = statistics.stdev(self._mi_history) if len(self._mi_history) >= 2 else 0.0
        toxic = afq < self.config.afq_threshold and lf < self.config.lf_threshold and mi > self.config.mi_sigma_multiplier * mi_std

        # Simple probability estimate
        prob = 0.0
        if toxic:
            prob = min(1.0, 0.5 + (abs(afq) + abs(lf)) / 2.0)

        return {
            "toxic": toxic,
            "probability": prob,
            "afq": afq,
            "lf": lf,
            "mi": mi,
            "recommendation": "passive" if prob > self.config.toxic_probability_threshold else "aggressive",
        }

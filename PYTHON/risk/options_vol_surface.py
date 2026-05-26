"""
risk/options_vol_surface.py — Options Volatility Surface Engine (Phase 5)
Module 27 from anatoliax_prompt_v6.txt

Features:
  - Implied volatility surface sigma_imp(K, T)
  - Skew engine: sigma_imp vs moneyness
  - Gamma exposure: Gamma = sum(partial²V/partialS² * open_interest)
  - Options flow intelligence: unusual volume, sweep detection
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class OptionStrike:
    strike: float
    expiry_days: float
    iv: float
    open_interest: float
    volume: float
    delta: float
    gamma: float
    theta: float
    vega: float


class OptionsVolatilitySurface:
    """
    Simplified SVI/SABR volatility surface + Greeks + gamma exposure.
    """

    def __init__(self, spot: float):
        self.spot = spot
        self._strikes: List[OptionStrike] = []

    def add_strike(self, strike: OptionStrike):
        self._strikes.append(strike)

    def svi_fit(self, strikes: List[float], ivs: List[float]) -> Dict[str, float]:
        """Simplified SVI parametric fit stub."""
        if len(strikes) < 3:
            return {}
        mean_iv = statistics.mean(ivs)
        return {"a": mean_iv * 0.5, "b": 0.1, "rho": -0.2, "m": 0.0, "sigma": 0.2}

    def gamma_exposure(self) -> float:
        """Aggregate gamma exposure by strike."""
        return sum(s.gamma * s.open_interest for s in self._strikes)

    def gamma_pinning(self) -> Optional[float]:
        """Predict pinning at max gamma strike."""
        if not self._strikes:
            return None
        max_gamma_strike = max(self._strikes, key=lambda s: s.gamma * s.open_interest)
        return max_gamma_strike.strike

    def detect_unusual_volume(self, threshold_sigma: float = 3.0) -> List[OptionStrike]:
        if len(self._strikes) < 2:
            return []
        mean_vol = statistics.mean(s.volume for s in self._strikes)
        std_vol = statistics.stdev(s.volume for s in self._strikes)
        if std_vol == 0:
            return []
        return [s for s in self._strikes if (s.volume - mean_vol) / std_vol > threshold_sigma]

    def detect_sweeps(self, time_tolerance_sec: float = 1.0) -> List[Dict]:
        """Sweep = multiple fills at same timestamp."""
        # Stub: would require timestamp data per fill
        return []

"""
s1_strategy.py — 1-Second VWAP Deviation Strategy

Uses 1-second bars (or tick-aggregated bars) to detect
VWAP deviation + volume spike. Fast execution.

Target: 0.05-0.2% per trade, hold 3-15s.
Max agents: 1.

Usage:
    from strategy.gold_mining.s1_strategy import S1Strategy
    strategy = S1Strategy()
    sig = strategy.generate(df)  # df: 1s bars
"""

import numpy as np
import pandas as pd
from typing import Optional


class S1Strategy:
    """
    1-second scalper: VWAP deviation + volume spike.
    """

    def __init__(
        self,
        vwap_period: int = 20,
        deviation_threshold: float = 0.001,
        volume_multiplier: float = 2.5,
        profit_target_pct: float = 0.1,
        stop_loss_pct: float = 0.05,
    ):
        self.vwap_period = vwap_period
        self.deviation_threshold = deviation_threshold
        self.volume_multiplier = volume_multiplier
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

    def generate(self, df: pd.DataFrame) -> Optional[dict]:
        """
        Generate signal from 1-second bar DataFrame.
        Returns signal dict or None.
        """
        if df.empty or len(df) < self.vwap_period:
            return None

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values

        recent_p = prices[-self.vwap_period:]
        recent_v = volumes[-self.vwap_period:]
        vwap = np.sum(recent_p * recent_v) / np.sum(recent_v)

        current_price = prices[-1]
        deviation = (current_price - vwap) / vwap if vwap > 0 else 0.0

        avg_vol = np.mean(volumes[-10:])
        vol_spike = volumes[-1] > avg_vol * self.volume_multiplier

        if deviation < -self.deviation_threshold and vol_spike:
            return self._signal("BUY", current_price, df.index[-1])
        if deviation > self.deviation_threshold and vol_spike:
            return self._signal("SELL", current_price, df.index[-1])
        return None

    def _signal(self, side: str, price: float, timestamp) -> dict:
        sl = price * (1.0 - self.stop_loss_pct) if side == "BUY" else price * (1.0 + self.stop_loss_pct)
        tp = price * (1.0 + self.profit_target_pct) if side == "BUY" else price * (1.0 - self.profit_target_pct)
        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "S1_VWAP_DEVIATION",
            "timestamp": timestamp,
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (3.0, 15.0),
        }

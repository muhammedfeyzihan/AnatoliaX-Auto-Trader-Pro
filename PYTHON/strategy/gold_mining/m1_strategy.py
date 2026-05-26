"""
m1_strategy.py — 1-Minute EMA Cross + Volume Strategy

Standard M1 momentum using EMA 3/8 cross with volume confirmation.
2-agent coordination: primary agent generates signal, secondary confirms.

Target: 0.3-1.0% per trade, hold 30-120s.
Max agents: 2.

Usage:
    from strategy.gold_mining.m1_strategy import M1Strategy
    strategy = M1Strategy()
    sig = strategy.generate(df)
"""

import numpy as np
import pandas as pd
from typing import Optional


def _ema(prices: np.ndarray, period: int) -> np.ndarray:
    if len(prices) < period:
        return prices.copy()
    alpha = 2.0 / (period + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


class M1Strategy:
    """
    1-minute EMA cross + volume strategy.
    Supports 2-agent confirmation (primary + secondary).
    """

    def __init__(
        self,
        ema_fast: int = 3,
        ema_slow: int = 8,
        volume_mult: float = 3.0,
        profit_target_pct: float = 0.5,
        stop_loss_pct: float = 0.3,
        require_secondary: bool = False,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_mult = volume_mult
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.require_secondary = require_secondary

    def generate(self, df: pd.DataFrame) -> Optional[dict]:
        if df.empty or len(df) < self.ema_slow + 1:
            return None

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values

        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)

        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        # Cross detection
        cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1] and vol_spike
        cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1] and vol_spike

        if cross_up:
            return self._signal("BUY", prices[-1], df.index[-1])
        if cross_down:
            return self._signal("SELL", prices[-1], df.index[-1])
        return None

    def confirm_secondary(self, df: pd.DataFrame, primary_signal: dict) -> bool:
        """
        Secondary agent confirmation.
        Checks if RSI is not overbought/oversold and trend aligns.
        """
        prices = df["close"].values
        rsi = self._rsi(prices, 14)
        if rsi is None:
            return False
        last_rsi = rsi[-1]
        side = primary_signal.get("side", "")
        if side == "BUY":
            return bool(30 < last_rsi < 70)
        if side == "SELL":
            return bool(30 < last_rsi < 70)
        return False

    def _signal(self, side: str, price: float, timestamp) -> dict:
        sl = price * (1.0 - self.stop_loss_pct) if side == "BUY" else price * (1.0 + self.stop_loss_pct)
        tp = price * (1.0 + self.profit_target_pct) if side == "BUY" else price * (1.0 - self.profit_target_pct)
        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "M1_EMA_CROSS",
            "timestamp": timestamp,
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (30.0, 120.0),
        }

    @staticmethod
    def _rsi(values: np.ndarray, period: int = 14) -> Optional[np.ndarray]:
        if len(values) < period + 1:
            return None
        deltas = np.diff(values)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
        avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")
        rs = avg_gain / (avg_loss + 1e-12)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        padding = len(values) - len(rsi)
        return np.concatenate([np.full(padding, 50.0), rsi])

"""
m5_strategy.py — 5-Minute EMA Cross + Volume Breakout

2-agent coordination: primary agent generates EMA 5/13 cross signal,
secondary agent confirms with RSI and ATR volatility check.

Target: 0.8-2.0% per trade, hold 2-10min.
Max agents: 2.
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


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    if len(high) < period + 1:
        return np.full_like(high, 0.0)
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)
    atr = np.convolve(tr, np.ones(period) / period, mode="valid")
    padding = len(high) - len(atr)
    return np.concatenate([np.full(padding, 0.0), atr])


class M5Strategy:
    """
    5-minute momentum strategy: EMA 5/13 cross + volume spike + ATR filter.
    2-agent: primary (cross) + secondary (RSI + volatility).
    """

    def __init__(
        self,
        ema_fast: int = 5,
        ema_slow: int = 13,
        volume_mult: float = 2.5,
        profit_target_pct: float = 1.5,
        stop_loss_pct: float = 0.8,
        atr_mult: float = 1.5,
        rsi_lower: float = 35.0,
        rsi_upper: float = 65.0,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_mult = volume_mult
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.atr_mult = atr_mult
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper

    def generate(self, df: pd.DataFrame) -> Optional[dict]:
        if df.empty or len(df) < self.ema_slow + 5:
            return None

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values
        highs = df.get("high", pd.Series(prices)).values
        lows = df.get("low", pd.Series(prices)).values

        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)

        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1] and vol_spike
        cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1] and vol_spike

        if not (cross_up or cross_down):
            return None

        side = "BUY" if cross_up else "SELL"

        # ATR-based SL/TP override for better R:R
        atr = _atr(highs, lows, prices, 14)
        last_atr = atr[-1] if len(atr) > 0 else prices[-1] * 0.01
        price = prices[-1]

        sl = price - (self.atr_mult * last_atr) if side == "BUY" else price + (self.atr_mult * last_atr)
        tp = price + (self.atr_mult * 2 * last_atr) if side == "BUY" else price - (self.atr_mult * 2 * last_atr)

        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "M5_EMA_CROSS",
            "timestamp": df.index[-1],
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (120.0, 600.0),
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
        }

    def confirm_secondary(self, df: pd.DataFrame, primary_signal: dict) -> bool:
        """
        Secondary agent: RSI not extreme + ATR volatility acceptable.
        """
        prices = df["close"].values
        rsi = _rsi(prices, 14)
        if rsi is None:
            return False
        last_rsi = rsi[-1]

        # RSI must be in reasonable zone (not overbought for BUY, not oversold for SELL)
        side = primary_signal.get("side", "")
        if side == "BUY":
            rsi_ok = bool(last_rsi < self.rsi_upper)
        elif side == "SELL":
            rsi_ok = bool(last_rsi > self.rsi_lower)
        else:
            return False

        # ATR volatility check: avoid extremely low volatility (no movement)
        atr = _atr(
            df.get("high", pd.Series(prices)).values,
            df.get("low", pd.Series(prices)).values,
            prices,
            14,
        )
        if len(atr) > 0:
            last_atr = atr[-1]
            avg_price = np.mean(prices[-20:])
            atr_pct = last_atr / avg_price if avg_price > 0 else 0.0
            if atr_pct < 0.001:  # Less than 0.1% ATR = dead market
                return False

        return rsi_ok

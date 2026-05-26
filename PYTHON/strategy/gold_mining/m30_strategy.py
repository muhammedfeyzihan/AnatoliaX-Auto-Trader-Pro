"""
m30_strategy.py — 30-Minute Trend Continuation Strategy

3-agent coordination: primary signal, risk confirmation, strategy consensus.
EMA 13/34 cross + volume + ATR filter with macro regime awareness.

Target: 2.5-7.0% per trade, hold 30min-2h.
Max agents: 3.

Usage:
    from strategy.gold_mining.m30_strategy import M30Strategy
    strategy = M30Strategy()
    result = strategy.generate(df, macro={"regime": "BULL"}, sentiment=0.2)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict

from strategy.parameter_registry import get_registry


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


class M30Strategy:
    """
    30-minute trend continuation with 3-agent consensus.
    Uses ParameterRegistry for regime-adaptive RSI thresholds and ATR multipliers.
    """

    def __init__(
        self,
        ema_fast: int = 13,
        ema_slow: int = 34,
        volume_mult: float = 2.0,
        profit_target_pct: float = 4.0,
        stop_loss_pct: float = 2.0,
        min_confidence: float = 70.0,
        consensus_required: float = 1.0,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_mult = volume_mult
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.min_confidence = min_confidence
        self.consensus_required = consensus_required

    def generate(self, df: pd.DataFrame, macro: Optional[dict] = None,
                 sentiment: float = 0.0) -> Optional[dict]:
        if df.empty or len(df) < self.ema_slow + 5:
            return None

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values
        highs = df.get("high", pd.Series(prices)).values
        lows = df.get("low", pd.Series(prices)).values

        # K95: Regime-adaptive config
        regime = macro.get("regime", "NEUTRAL").lower() if macro else "neutral"
        cfg = get_registry().get_signal_config(regime=regime)

        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)

        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1] and vol_spike
        cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1] and vol_spike

        if not (cross_up or cross_down):
            return None

        side = "BUY" if cross_up else "SELL"

        # Agent B: Risk check with adaptive thresholds
        regime_ok = regime in ("bull", "neutral")
        if side == "SELL" and regime == "bull":
            regime_ok = False
        if side == "BUY" and regime == "bear":
            regime_ok = False

        sentiment_ok = abs(sentiment) < 0.7

        # Agent C: Confidence with adaptive RSI thresholds
        rsi = _rsi(prices, 14)
        last_rsi = rsi[-1] if rsi is not None else 50.0
        rsi_ok = cfg.rsi_lower < last_rsi < cfg.rsi_upper

        atr = _atr(highs, lows, prices, 14)
        last_atr = atr[-1] if len(atr) > 0 else prices[-1] * 0.03
        r_r = self.profit_target_pct / self.stop_loss_pct

        confidence = self._compute_confidence(
            cross_up, vol_spike, regime_ok, sentiment_ok, rsi_ok, r_r
        )

        if confidence < self.min_confidence:
            return None

        votes = {
            "technical": True,
            "risk": regime_ok and sentiment_ok,
            "strategy": confidence >= self.min_confidence and rsi_ok,
        }
        consensus_pct = sum(votes.values()) / len(votes)
        if consensus_pct < self.consensus_required:
            return None

        price = prices[-1]
        sl_dist = last_atr * cfg.atr_sl_mult
        tp_dist = last_atr * cfg.atr_tp1_mult
        sl = price - sl_dist if side == "BUY" else price + sl_dist
        tp = price + tp_dist if side == "BUY" else price - tp_dist

        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "M30_3AGENT_CONSENSUS",
            "timestamp": df.index[-1],
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (1800.0, 7200.0),
            "confidence": round(confidence, 1),
            "consensus": votes,
            "consensus_pct": round(consensus_pct, 2),
            "regime": regime,
        }

    def _compute_confidence(self, cross_up: bool, vol_spike: bool,
                           regime_ok: bool, sentiment_ok: bool, rsi_ok: bool, r_r: float) -> float:
        score = 50.0
        score += 15 if cross_up else 0
        score += 10 if vol_spike else 0
        score += 10 if regime_ok else -10
        score += 5 if sentiment_ok else -5
        score += 10 if rsi_ok else -5
        score += min(20, r_r * 5)
        return min(100.0, max(0.0, score))

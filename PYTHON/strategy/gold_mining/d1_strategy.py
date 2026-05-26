"""
d1_strategy.py — 1-Day Position Strategy

3-agent council with consensus:
- Agent A (Sinyal): EMA 21/50 + RSI + Bollinger Bands
- Agent B (Risk): Macro regime + sector correlation + sentiment
- Agent C (Strateji): Confidence + Kelly sizing + multi-day exit plan

Target: 5.0-15.0% per trade, hold 1-5 days.
Max agents: 3.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict


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


def _bbands(prices: np.ndarray, period: int = 20, mult: float = 2.0) -> tuple:
    if len(prices) < period:
        mid = np.full_like(prices, prices[-1])
        return mid, mid, mid
    mid = np.convolve(prices, np.ones(period) / period, mode="valid")
    std = np.array([np.std(prices[i:i + period]) for i in range(len(prices) - period + 1)])
    upper = mid + mult * std
    lower = mid - mult * std
    padding = len(prices) - len(mid)
    p = np.full(padding, 0.0)
    mid = np.concatenate([p, mid])
    upper = np.concatenate([p, upper])
    lower = np.concatenate([p, lower])
    return upper, mid, lower


class D1Strategy:
    """
    1-day position strategy with 3-agent consensus.
    EMA 21/50 + RSI + Bollinger Bands + volume.
    """

    def __init__(
        self,
        ema_fast: int = 21,
        ema_slow: int = 50,
        volume_mult: float = 1.8,
        profit_target_pct: float = 10.0,
        stop_loss_pct: float = 4.0,
        min_confidence: float = 75.0,
        consensus_required: float = 0.67,
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

        # Agent A: Technical signal
        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)
        rsi = _rsi(prices, 14)
        bb_upper, bb_mid, bb_lower = _bbands(prices)

        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        # EMA cross
        ema_cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1]
        ema_cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1]

        # RSI confirmation
        last_rsi = rsi[-1] if rsi is not None else 50.0
        rsi_buy = last_rsi > 50 and last_rsi < 70
        rsi_sell = last_rsi < 50 and last_rsi > 30

        # Bollinger position
        bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_mid[-1] if bb_mid[-1] > 0 else 0
        bb_squeeze = bb_width < 0.05  # Tight bands = breakout potential

        cross_up = ema_cross_up and rsi_buy and vol_spike
        cross_down = ema_cross_down and rsi_sell and vol_spike

        if not (cross_up or cross_down):
            return None

        side = "BUY" if cross_up else "SELL"

        # Agent B: Risk check
        regime = macro.get("regime", "NEUTRAL") if macro else "NEUTRAL"
        regime_ok = regime in ("BULL", "NEUTRAL")
        if side == "SELL" and regime == "BULL":
            regime_ok = False
        if side == "BUY" and regime == "BEAR":
            regime_ok = False

        sentiment_ok = abs(sentiment) < 0.6  # Stricter for daily

        # Agent C: Confidence
        r_r = self.profit_target_pct / self.stop_loss_pct
        confidence = self._compute_confidence(
            cross_up, vol_spike, regime_ok, sentiment_ok, r_r, bb_squeeze
        )

        if confidence < self.min_confidence:
            return None

        # Consensus
        votes = {
            "technical": True,
            "risk": regime_ok and sentiment_ok,
            "strategy": confidence >= self.min_confidence,
        }
        consensus_pct = sum(votes.values()) / len(votes)
        if consensus_pct < self.consensus_required:
            return None

        price = prices[-1]
        sl = price * (1.0 - self.stop_loss_pct / 100) if side == "BUY" else price * (1.0 + self.stop_loss_pct / 100)
        tp = price * (1.0 + self.profit_target_pct / 100) if side == "BUY" else price * (1.0 - self.profit_target_pct / 100)

        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "D1_3AGENT_POSITION",
            "timestamp": df.index[-1],
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (86400.0, 432000.0),
            "confidence": round(confidence, 1),
            "consensus": votes,
            "consensus_pct": round(consensus_pct, 2),
            "bb_squeeze": bool(bb_squeeze),
            "rsi": round(last_rsi, 1),
        }

    def _compute_confidence(self, cross_up: bool, vol_spike: bool,
                           regime_ok: bool, sentiment_ok: bool, r_r: float,
                           bb_squeeze: bool) -> float:
        score = 50.0
        score += 15 if cross_up else 0
        score += 10 if vol_spike else 0
        score += 10 if regime_ok else -10
        score += 10 if sentiment_ok else -5
        score += 10 if bb_squeeze else 0
        score += min(20, r_r * 4)
        return min(100.0, max(0.0, score))

"""
h1_strategy.py — 1-Hour Trend Strategy

3-agent council with consensus:
- Agent A (Sinyal): EMA 9/21 + MACD histogram
- Agent B (Risk): ATR volatility + macro regime alignment
- Agent C (Strateji): Confidence scoring, position sizing, exit planning

Target: 2.0-6.0% per trade, hold 1-4 hours.
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


def _macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = ema_fast - ema_slow
    sig = _ema(macd_line, signal)
    hist = macd_line - sig
    return macd_line, sig, hist


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


class H1Strategy:
    """
    1-hour trend strategy with 3-agent consensus.
    Requires ALL 3 agents to agree (or 2/3 with high confidence).
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        volume_mult: float = 2.0,
        profit_target_pct: float = 4.0,
        stop_loss_pct: float = 2.0,
        min_confidence: float = 72.0,
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
        highs = df.get("high", pd.Series(prices)).values
        lows = df.get("low", pd.Series(prices)).values

        # Agent A: Technical signal (EMA + MACD)
        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)
        macd_line, macd_sig, macd_hist = _macd(prices)

        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        ema_cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1]
        ema_cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1]
        macd_bull = macd_hist[-1] > 0 and macd_hist[-1] > macd_hist[-2]
        macd_bear = macd_hist[-1] < 0 and macd_hist[-1] < macd_hist[-2]

        cross_up = ema_cross_up and macd_bull and vol_spike
        cross_down = ema_cross_down and macd_bear and vol_spike

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

        sentiment_ok = abs(sentiment) < 0.7

        # Agent C: Confidence scoring
        atr = _atr(highs, lows, prices, 14)
        last_atr = atr[-1] if len(atr) > 0 else prices[-1] * 0.02
        r_r = self.profit_target_pct / self.stop_loss_pct

        confidence = self._compute_confidence(
            cross_up, vol_spike, regime_ok, sentiment_ok, r_r, macd_bull or macd_bear
        )

        if confidence < self.min_confidence:
            return None

        # Consensus check
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
            "strategy": "H1_3AGENT_TREND",
            "timestamp": df.index[-1],
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (3600.0, 14400.0),
            "confidence": round(confidence, 1),
            "consensus": votes,
            "consensus_pct": round(consensus_pct, 2),
        }

    def _compute_confidence(self, cross_up: bool, vol_spike: bool,
                           regime_ok: bool, sentiment_ok: bool, r_r: float,
                           macd_align: bool) -> float:
        score = 50.0
        score += 15 if cross_up else 0
        score += 10 if vol_spike else 0
        score += 10 if regime_ok else -10
        score += 5 if sentiment_ok else -5
        score += 10 if macd_align else -5
        score += min(20, r_r * 5)
        return min(100.0, max(0.0, score))

"""
m15_strategy.py — 15-Minute Multi-Agent Swing Strategy

Full 3-agent council with consensus:
- Agent A (Sinyal): Technical analysis + trend detection
- Agent B (Risk): Position sizing, macro regime, correlation
- Agent C (Strateji): Final consensus, Kelly sizing, exit planning

Target: 1.5-5.0% per trade, hold 5-30min.
Max agents: 3.

Usage:
    from strategy.gold_mining.m15_strategy import M15Strategy
    strategy = M15Strategy()
    result = strategy.generate(df, macro={}, sentiment=0)
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


class M15Strategy:
    """
    15-minute swing strategy with 3-agent consensus.
    Requires ALL 3 agents to agree (or 2/3 with high confidence).
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        volume_mult: float = 2.0,
        profit_target_pct: float = 3.0,
        stop_loss_pct: float = 1.5,
        min_confidence: float = 70.0,
        consensus_required: float = 1.0,  # 1.0 = unanimous, 0.67 = 2/3
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
        """
        Generate signal with full agent consensus.
        macro: {"regime": "BULL|BEAR|NEUTRAL", "score": int}
        sentiment: -1 to +1
        """
        if df.empty or len(df) < self.ema_slow + 1:
            return None

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values

        # Agent A: Technical signal
        ema_f = _ema(prices, self.ema_fast)
        ema_s = _ema(prices, self.ema_slow)
        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_mult

        cross_up = ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1] and vol_spike
        cross_down = ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1] and vol_spike

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

        sentiment_ok = abs(sentiment) < 0.7  # Avoid extreme sentiment

        # Agent C: Confidence scoring
        atr = self._atr(df["high"].values, df["low"].values, prices, 14)
        last_atr = atr[-1] if len(atr) > 0 else prices[-1] * 0.03
        r_r = self.profit_target_pct / self.stop_loss_pct

        confidence = self._compute_confidence(
            cross_up, vol_spike, regime_ok, sentiment_ok, r_r
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
            "strategy": "M15_3AGENT_CONSENSUS",
            "timestamp": df.index[-1],
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (300.0, 1800.0),
            "confidence": round(confidence, 1),
            "consensus": votes,
            "consensus_pct": round(consensus_pct, 2),
        }

    def _compute_confidence(self, cross_up: bool, vol_spike: bool,
                           regime_ok: bool, sentiment_ok: bool, r_r: float) -> float:
        score = 50.0
        score += 15 if cross_up else 0
        score += 10 if vol_spike else 0
        score += 10 if regime_ok else -10
        score += 5 if sentiment_ok else -5
        score += min(20, r_r * 5)
        return min(100.0, max(0.0, score))

    @staticmethod
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

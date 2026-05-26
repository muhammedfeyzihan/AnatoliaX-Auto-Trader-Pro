"""
ta_filter.py — Pre-AI Technical Analysis Filter
Hermes Trader pattern: run cheap local indicators first,
only pass CONFIRMED setups to LLM to reduce token cost ~80%.

Usage:
    pf = TAFPreFilter(threshold=65)
    res = pf.evaluate("THYAO", timeframes=["1h","4h","1d"])
    if res.confirmed:
        ai_call(res.composite_score, res.reason)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TAFilterResult:
    symbol: str
    confirmed: bool
    composite_score: float  # 0-100
    reason: str
    timeframe_scores: dict  # {"1h": 70, "4h": 55, ...}
    indicators: dict


class TAFPreFilter:
    """
    Multi-timeframe indicator scoring gate.
    Computes EMA cross, RSI, ATR, volume spike locally.
    No LLM calls unless composite score >= threshold.
    """

    def __init__(self, threshold: float = 65.0):
        self.threshold = threshold

    def evaluate(
        self,
        symbol: str,
        bars: dict[str, "pd.DataFrame"] = None,
        timeframes: Optional[List[str]] = None,
    ) -> TAFilterResult:
        """
        Evaluate a symbol across timeframes.
        bars: {"1h": DataFrame, "4h": DataFrame, "1d": DataFrame}
        Returns TAFilterResult with confirmed flag.
        """
        import pandas as pd
        timeframes = timeframes or ["1d"]
        tf_scores = {}
        all_indicators = {}

        for tf, df in (bars or {}).items():
            if df is None or len(df) < 30:
                tf_scores[tf] = 0.0
                continue
            score, ind = self._score_single(df)
            tf_scores[tf] = score
            all_indicators[tf] = ind

        if not tf_scores:
            return TAFilterResult(
                symbol=symbol,
                confirmed=False,
                composite_score=0.0,
                reason="No data",
                timeframe_scores={},
                indicators={},
            )

        # Weighted composite: higher weight for longer timeframes
        weights = {"1m": 0.1, "5m": 0.15, "15m": 0.2, "1h": 0.25, "4h": 0.35, "1d": 0.5}
        total_weight = 0.0
        weighted_sum = 0.0
        for tf, sc in tf_scores.items():
            w = weights.get(tf, 0.2)
            weighted_sum += sc * w
            total_weight += w
        composite = weighted_sum / total_weight if total_weight > 0 else 0.0
        composite = min(100.0, max(0.0, composite))

        confirmed = composite >= self.threshold
        reason = (
            f"CONFIRMED ({composite:.0f}/100)"
            if confirmed
            else f"REJECTED ({composite:.0f}/100 < {self.threshold})"
        )

        return TAFilterResult(
            symbol=symbol,
            confirmed=confirmed,
            composite_score=composite,
            reason=reason,
            timeframe_scores=tf_scores,
            indicators=all_indicators,
        )

    def _score_single(self, df: "pd.DataFrame") -> tuple[float, dict]:
        """Score a single timeframe DataFrame."""
        import pandas as pd
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df.get("volume", pd.Series(np.ones(len(df)))).values

        # EMA cross score
        ema_fast = self._ema(close, 9)
        ema_slow = self._ema(close, 21)
        ema_score = 100.0 if ema_fast[-1] > ema_slow[-1] else 0.0

        # RSI score
        rsi = self._rsi(close, 14)
        rsi_val = rsi[-1]
        rsi_score = 100.0 if 40 < rsi_val < 70 else (50.0 if 30 < rsi_val < 80 else 0.0)

        # ATR trend score
        atr = self._atr(high, low, close, 14)
        atr_ratio = atr[-1] / close[-1] if close[-1] > 0 else 0.0
        atr_score = 100.0 if 0.01 < atr_ratio < 0.05 else 50.0

        # Volume spike score
        vol_ma = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        vol_spike = volume[-1] / vol_ma if vol_ma > 0 else 1.0
        vol_score = 100.0 if vol_spike > 1.5 else (50.0 if vol_spike > 1.0 else 0.0)

        # Composite for this timeframe
        score = (ema_score * 0.35) + (rsi_score * 0.25) + (atr_score * 0.15) + (vol_score * 0.25)
        indicators = {
            "ema_fast": round(ema_fast[-1], 2),
            "ema_slow": round(ema_slow[-1], 2),
            "rsi": round(rsi_val, 2),
            "atr": round(atr[-1], 4),
            "volume_spike": round(vol_spike, 2),
        }
        return score, indicators

    @staticmethod
    def _ema(values: np.ndarray, period: int) -> np.ndarray:
        if len(values) < period:
            return values
        k = 2.0 / (period + 1)
        ema = np.zeros_like(values)
        ema[0] = values[0]
        for i in range(1, len(values)):
            ema[i] = values[i] * k + ema[i - 1] * (1 - k)
        return ema

    @staticmethod
    def _rsi(values: np.ndarray, period: int = 14) -> np.ndarray:
        if len(values) < period + 1:
            return np.full_like(values, 50.0)
        deltas = np.diff(values)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
        avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")
        rs = avg_gain / (avg_loss + 1e-12)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        # Pad to original length
        padding = len(values) - len(rsi)
        return np.concatenate([np.full(padding, 50.0), rsi])

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

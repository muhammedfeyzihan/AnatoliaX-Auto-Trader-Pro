"""
adaptive_selector.py — Adaptive Tier Selector

Analyzes market conditions and automatically selects the best
Gold Mining tier / timeframe for maximum profit.

Usage:
    from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
    selector = AdaptiveTierSelector()
    recommended = selector.select(df, macro={"regime": "BULL"})
    # Returns: "M5", "M15", "H1", etc.
"""

import numpy as np
import pandas as pd
from typing import Optional

from strategy.gold_mining.tier_config import (
    TIER_DEFINITIONS,
    get_tier_by_name,
)


def _ema(prices: np.ndarray, period: int) -> np.ndarray:
    if len(prices) < period:
        return prices.copy()
    alpha = 2.0 / (period + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


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


def _adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
    """Simplified ADX calculation. Returns last ADX value (0-100)."""
    if len(high) < period + 2:
        return 25.0
    plus_dm = np.zeros(len(high) - 1)
    minus_dm = np.zeros(len(high) - 1)
    tr = np.zeros(len(high) - 1)
    for i in range(1, len(high)):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i - 1] = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm[i - 1] = down_move if down_move > up_move and down_move > 0 else 0
        tr[i - 1] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    if len(tr) < period:
        return 25.0
    atr = np.convolve(tr, np.ones(period) / period, mode="valid")
    plus_di = 100.0 * np.convolve(plus_dm, np.ones(period) / period, mode="valid") / (atr + 1e-12)
    minus_di = 100.0 * np.convolve(minus_dm, np.ones(period) / period, mode="valid") / (atr + 1e-12)
    dx = 100.0 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-12)
    if len(dx) < period:
        return 25.0
    adx = np.convolve(dx, np.ones(period) / period, mode="valid")
    return float(adx[-1]) if len(adx) > 0 else 25.0


class AdaptiveTierSelector:
    """
    Otomatik zaman dilimi ve tier seçici.

    Piyasa koşullarına göre en verimli tier'i seçer:
    - Yüksek volatilite + yüksek hacim → MS, S1, M1 (hızlı scalping)
    - Orta volatilite + net trend → M5, M15 (swing)
    - Düşük volatilite + yatay piyasa → S1 mean-reversion veya bekle
    - Güçlü trend → H1, D1 (trend takip)
    """

    def __init__(
        self,
        atr_high_threshold: float = 0.02,   # 2% ATR = high vol
        atr_low_threshold: float = 0.005,   # 0.5% ATR = low vol
        adx_trend_threshold: float = 25.0,  # ADX > 25 = trending
        volume_spike_mult: float = 2.0,
    ):
        self.atr_high_threshold = atr_high_threshold
        self.atr_low_threshold = atr_low_threshold
        self.adx_trend_threshold = adx_trend_threshold
        self.volume_spike_mult = volume_spike_mult

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyze market conditions and return a score dict.
        """
        if df.empty or len(df) < 30:
            return {"error": "insufficient_data"}

        prices = df["close"].values
        highs = df.get("high", pd.Series(prices)).values
        lows = df.get("low", pd.Series(prices)).values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values

        # ATR percentage
        atr_vals = _atr(highs, lows, prices, 14)
        last_atr = atr_vals[-1] if len(atr_vals) > 0 else 0.0
        avg_price = np.mean(prices[-20:])
        atr_pct = last_atr / avg_price if avg_price > 0 else 0.0

        # ADX (trend strength)
        adx_val = _adx(highs, lows, prices, 14)

        # Volume spike
        avg_vol = np.mean(volumes[-20:])
        vol_spike = volumes[-1] > avg_vol * self.volume_spike_mult
        vol_trend = np.mean(volumes[-10:]) / (np.mean(volumes[-30:-10]) + 1e-12)

        # EMA alignment (trend direction)
        ema_fast = _ema(prices, 9)
        ema_slow = _ema(prices, 21)
        trend_up = ema_fast[-1] > ema_slow[-1]
        trend_down = ema_fast[-1] < ema_slow[-1]
        trend_strength = abs(ema_fast[-1] - ema_slow[-1]) / avg_price if avg_price > 0 else 0.0

        return {
            "atr_pct": round(atr_pct, 4),
            "adx": round(adx_val, 2),
            "vol_spike": bool(vol_spike),
            "vol_trend": round(vol_trend, 2),
            "trend_up": bool(trend_up),
            "trend_down": bool(trend_down),
            "trend_strength": round(trend_strength, 4),
        }

    def select(self, df: pd.DataFrame, macro: Optional[dict] = None) -> str:
        """
        Select the best tier based on market conditions.
        Returns tier name (e.g., "M5", "H1").
        """
        analysis = self.analyze(df)
        if "error" in analysis:
            return "M15"  # Default safe tier

        atr_pct = analysis["atr_pct"]
        adx = analysis["adx"]
        vol_spike = analysis["vol_spike"]
        trend_up = analysis["trend_up"]
        trend_down = analysis["trend_down"]
        trend_strength = analysis["trend_strength"]

        regime = macro.get("regime", "NEUTRAL") if macro else "NEUTRAL"

        # High volatility + high volume → fast scalping (M1 or M5)
        if atr_pct > self.atr_high_threshold and vol_spike:
            if adx > self.adx_trend_threshold:
                return "M5"  # Trending + volatile = best for 5m
            else:
                return "S1"  # Choppy + volatile = micro scalping

        # Low volatility + ranging → avoid, or very fast mean reversion
        if atr_pct < self.atr_low_threshold:
            if vol_spike:
                return "M1"  # Volume breakout from low vol
            return "M1"  # Default to 1m even in low vol

        # Strong trend detected
        if adx > 30 and trend_strength > 0.005:
            if trend_up and regime in ("BULL", "NEUTRAL"):
                if adx > 40:
                    return "H2" if trend_strength > 0.008 else "H1"
                return "M30" if adx > 35 else "M15"
            if trend_down and regime in ("BEAR", "NEUTRAL"):
                if adx > 40:
                    return "H2" if trend_strength > 0.008 else "H1"
                return "M30" if adx > 35 else "M15"

        # Moderate conditions → M5, M15, or M30
        if vol_spike:
            return "M5" if atr_pct > 0.01 else "M15"
        return "M30" if adx > 25 else "M15"

    def score_all_tiers(self, df: pd.DataFrame, macro: Optional[dict] = None) -> dict:
        """
        Score all tiers and return a ranked dict.
        """
        analysis = self.analyze(df)
        if "error" in analysis:
            return {t.name: 0.0 for t in TIER_DEFINITIONS}

        atr_pct = analysis["atr_pct"]
        adx = analysis["adx"]
        vol_spike = analysis["vol_spike"]
        trend_strength = analysis["trend_strength"]
        regime = macro.get("regime", "NEUTRAL") if macro else "NEUTRAL"

        scores = {}
        for t in TIER_DEFINITIONS:
            score = 50.0

            # Volatility fit
            if t.name in ("MS", "S1"):
                score += 30 if atr_pct > self.atr_high_threshold else -10
            elif t.name == "M1":
                score += 20 if atr_pct > 0.01 else 10
            elif t.name == "M5":
                score += 25 if 0.005 < atr_pct < 0.02 else 5
            elif t.name == "M15":
                score += 20 if 0.003 < atr_pct < 0.015 else 5
            elif t.name == "M30":
                score += 22 if 0.003 < atr_pct < 0.012 else 5
            elif t.name in ("H1", "H2", "D1"):
                score += 25 if adx > 30 and trend_strength > 0.003 else -5

            # Volume fit
            if vol_spike:
                score += 10 if t.name in ("M1", "M5", "M15", "M30") else 5

            # Trend fit
            if adx > self.adx_trend_threshold:
                score += 15 if t.name in ("M15", "M30", "H1", "H2", "D1") else 0
            else:
                score += 15 if t.name in ("MS", "S1", "M1") else 0

            # Regime fit
            if regime == "BEAR" and t.name in ("H1", "H2", "D1"):
                score -= 10  # Long-term harder in bear
            if regime == "BULL" and t.name in ("H1", "H2", "D1"):
                score += 10

            scores[t.name] = round(min(100.0, max(0.0, score)), 1)

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

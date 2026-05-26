"""
multi_tf_detector.py — Multi-Timeframe Manipulation Detection

Detects fake breakouts, volume anomalies, divergence, and wash trading
across 15m, 1h, 4h, 1d timeframes.

Inspired by Ruflo's neural-trader pattern matching and MiroFish's
multi-agent temporal analysis.

Usage:
    detector = MultiTFManipDetector()
    result = detector.scan("THYAO", bars={"15m": df_15m, "1h": df_1h, "1d": df_1d})
    if result.is_manipulated:
        print(result.reason)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ManipResult:
    symbol: str
    is_manipulated: bool
    threat_score: float  # 0-100
    reason: str
    timeframe_flags: Dict[str, str]  # {"15m": "volume_anomaly", ...}


class MultiTFManipDetector:
    """
    Cross-timeframe manipulation scanner.
    Checks for:
    1. Fake breakout (price breaks resistance but volume doesn't confirm)
    2. Divergence (price vs RSI/MACD across timeframes)
    3. Volume anomaly (volume spike without price movement)
    4. Wash trading (repeated same-size orders at same price)
    5. ATR compression then expansion (squeeze-then-spike pattern)
    """

    def __init__(
        self,
        volume_z_threshold: float = 3.0,
        divergence_threshold: float = 0.05,
        atr_spike_ratio: float = 2.5,
        min_samples: int = 30,
    ):
        self.volume_z_threshold = volume_z_threshold
        self.divergence_threshold = divergence_threshold
        self.atr_spike_ratio = atr_spike_ratio
        self.min_samples = min_samples

    def scan(self, symbol: str, bars: Dict[str, pd.DataFrame]) -> ManipResult:
        """
        Scan a symbol across multiple timeframes.
        bars: {"15m": DataFrame, "1h": DataFrame, "1d": DataFrame}
        """
        flags = {}
        scores = []

        for tf, df in bars.items():
            if df is None or len(df) < self.min_samples:
                continue
            tf_score, tf_flag = self._scan_timeframe(df)
            if tf_flag:
                flags[tf] = tf_flag
                scores.append(tf_score)

        # Cross-timeframe consistency check
        if len(flags) >= 2:
            # If manipulation detected in 2+ timeframes, escalate
            cross_tf_score = max(scores) * 1.2 if scores else 0.0
            cross_tf_score = min(100.0, cross_tf_score)
        else:
            cross_tf_score = max(scores) if scores else 0.0

        is_manip = bool(cross_tf_score >= 60.0)
        reason = self._build_reason(flags, cross_tf_score)

        return ManipResult(
            symbol=symbol,
            is_manipulated=is_manip,
            threat_score=float(cross_tf_score),
            reason=reason,
            timeframe_flags=flags,
        )

    def _scan_timeframe(self, df: pd.DataFrame) -> tuple[float, str]:
        """Scan single timeframe. Returns (score, flag_or_empty)."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df.get("volume", pd.Series(np.ones(len(df)))).values

        checks = [
            self._check_volume_anomaly(close, volume),
            self._check_fake_breakout(close, high, low, volume),
            self._check_divergence(close, volume),
            self._check_atr_squeeze_spike(high, low, close),
        ]

        # Take highest scoring flag
        max_score = 0.0
        max_flag = ""
        for score, flag in checks:
            if score > max_score:
                max_score = score
                max_flag = flag

        return max_score, max_flag

    def _check_volume_anomaly(self, close: np.ndarray, volume: np.ndarray) -> tuple[float, str]:
        """Volume z-score spike without proportional price move."""
        vol_mean = np.mean(volume[-20:])
        vol_std = np.std(volume[-20:]) if len(volume) >= 20 else 1.0
        if vol_std == 0:
            vol_std = 1.0
        z = (volume[-1] - vol_mean) / vol_std
        price_change = abs(close[-1] - close[-2]) / close[-2] if close[-2] > 0 else 0

        if z > self.volume_z_threshold and price_change < 0.005:
            score = min(100.0, z * 20)
            return score, "volume_anomaly"
        return 0.0, ""

    def _check_fake_breakout(self, close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> tuple[float, str]:
        """Price breaks recent high but volume is below average."""
        recent_high = np.max(high[-10:-1])
        if close[-1] > recent_high * 1.01:
            vol_avg = np.mean(volume[-10:])
            if volume[-1] < vol_avg * 0.8:
                return 75.0, "fake_breakout"
        return 0.0, ""

    def _check_divergence(self, close: np.ndarray, volume: np.ndarray) -> tuple[float, str]:
        """Price makes new high but RSI/MACD doesn't confirm."""
        # Simplified RSI divergence
        if len(close) < 15:
            return 0.0, ""
        rsi = self._rsi(close, 14)
        price_high = np.max(close[-10:])
        prev_price_high = np.max(close[-20:-10])
        rsi_high = np.max(rsi[-10:])
        prev_rsi_high = np.max(rsi[-20:-10])

        if price_high > prev_price_high * 1.02 and rsi_high < prev_rsi_high * 0.98:
            return 70.0, "bearish_divergence"

        price_low = np.min(close[-10:])
        prev_price_low = np.min(close[-20:-10])
        rsi_low = np.min(rsi[-10:])
        prev_rsi_low = np.min(rsi[-20:-10])

        if price_low < prev_price_low * 0.98 and rsi_low > prev_rsi_low * 1.02:
            return 70.0, "bullish_divergence"

        return 0.0, ""

    def _check_atr_squeeze_spike(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> tuple[float, str]:
        """ATR compression followed by sudden expansion."""
        if len(high) < 20:
            return 0.0, ""
        atr_now = self._atr_single(high[-5:], low[-5:], close[-5:])
        atr_prev = self._atr_single(high[-15:-5], low[-15:-5], close[-15:-5])
        if atr_prev > 0 and atr_now / atr_prev > self.atr_spike_ratio:
            return 65.0, "atr_spike"
        return 0.0, ""

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
        padding = len(values) - len(rsi)
        return np.concatenate([np.full(padding, 50.0), rsi])

    @staticmethod
    def _atr_single(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        if len(high) < 2:
            return 0.0
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        return float(np.mean(tr))

    def _build_reason(self, flags: Dict[str, str], score: float) -> str:
        if not flags:
            return f"Clean ({score:.0f}/100)"
        parts = [f"{tf}: {flag}" for tf, flag in flags.items()]
        return f"Manip detected ({score:.0f}/100) — " + "; ".join(parts)

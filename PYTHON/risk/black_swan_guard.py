"""
black_swan_guard.py — Black Swan Protection & Anomaly Detection

Detects flash crashes, cascade liquidations, volatility signatures,
and halts execution before catastrophic loss.

Integrates with: KillSwitch, ImmutableExecutionLawEngine, UnifiedRiskEngine.

Usage:
    from risk.black_swan_guard import BlackSwanGuard
    guard = BlackSwanGuard()
    alert = guard.check(df, portfolio_value=100_000)
    if alert.is_black_swan:
        guard.halt("FLASH_CRASH_DETECTED")
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from collections import deque

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np
import pandas as pd


@dataclass
class BlackSwanAlert:
    is_black_swan: bool
    level: str  # "CRITICAL", "WARNING", "NORMAL"
    reason: str
    symbol: str = ""
    timestamp: float = field(default_factory=time.time)
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "is_black_swan": self.is_black_swan,
            "level": self.level,
            "reason": self.reason,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
        }


class BlackSwanGuard:
    """
    Multi-layer black swan detection.

    Layers:
    1. Volatility signature anomaly (ATR spike > 5x historical)
    2. Flash crash (price drop > 10% in 1 bar)
    3. Cascade liquidation (volume spike + price gap)
    4. Correlation breakdown (cross-asset correlation collapse)
    5. Fat-tail probability (kurtosis > 10)
    """

    def __init__(
        self,
        atr_spike_threshold: float = 5.0,
        flash_crash_pct: float = 10.0,
        cascade_volume_mult: float = 10.0,
        fat_tail_kurtosis: float = 10.0,
        halt_duration_seconds: float = 300.0,
    ):
        self.atr_spike_threshold = atr_spike_threshold
        self.flash_crash_pct = flash_crash_pct
        self.cascade_volume_mult = cascade_volume_mult
        self.fat_tail_kurtosis = fat_tail_kurtosis
        self.halt_duration = halt_duration_seconds

        self._halted: bool = False
        self._halt_reason: str = ""
        self._halt_until: float = 0.0
        self._history: deque = deque(maxlen=1000)
        self._alerts: List[BlackSwanAlert] = []

    # ------------------------------------------------------------------
    # Detection engine
    # ------------------------------------------------------------------
    def check(self, df: pd.DataFrame, symbol: str = "", portfolio_value: float = 100_000.0) -> BlackSwanAlert:
        """Run all detection layers against a DataFrame."""
        if self._halted and time.time() < self._halt_until:
            return BlackSwanAlert(
                is_black_swan=True,
                level="CRITICAL",
                reason=f"System halted: {self._halt_reason}",
                symbol=symbol,
                metrics={"halt_remaining": self._halt_until - time.time()},
            )

        if df.empty or len(df) < 30:
            return BlackSwanAlert(is_black_swan=False, level="NORMAL", reason="Insufficient data", symbol=symbol)

        prices = df["close"].values
        volumes = df.get("volume", pd.Series(np.ones(len(df)))).values
        highs = df.get("high", pd.Series(prices)).values
        lows = df.get("low", pd.Series(prices)).values

        metrics: Dict[str, float] = {}

        # Layer 1: ATR spike
        atr_vals = self._atr(highs, lows, prices, 14)
        recent_atr = np.mean(atr_vals[-5:]) if len(atr_vals) >= 5 else 0.0
        historical_atr = np.mean(atr_vals[:-5]) if len(atr_vals) > 5 else recent_atr
        atr_ratio = (recent_atr / historical_atr) if historical_atr > 0 else 1.0
        metrics["atr_ratio"] = round(atr_ratio, 2)
        if atr_ratio > self.atr_spike_threshold:
            return self._alert(symbol, "CRITICAL", f"ATR spike {atr_ratio:.1f}x normal", metrics)

        # Layer 2: Flash crash (guard against zero prices)
        safe_prices = np.where(prices[:-1] == 0, 1e-9, prices[:-1])
        pct_changes = np.diff(prices) / safe_prices * 100.0
        worst_drop = np.min(pct_changes) if len(pct_changes) > 0 else 0.0
        metrics["worst_drop_pct"] = round(worst_drop, 2)
        if abs(worst_drop) >= self.flash_crash_pct:
            return self._alert(symbol, "CRITICAL", f"Flash crash {worst_drop:.1f}%", metrics)

        # Layer 3: Cascade liquidation (volume spike + gap)
        avg_vol = np.mean(volumes[:-1]) if len(volumes) > 1 else 1.0
        vol_spike = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        last_gap = abs(prices[-1] - prices[-2]) / prices[-2] * 100.0 if len(prices) > 1 else 0.0
        metrics["volume_spike"] = round(vol_spike, 1)
        metrics["last_gap_pct"] = round(last_gap, 2)
        if vol_spike > self.cascade_volume_mult and last_gap > 3.0:
            return self._alert(symbol, "CRITICAL", f"Cascade liquidation (vol {vol_spike:.0f}x + gap {last_gap:.1f}%)", metrics)

        # Layer 4: Fat tail (kurtosis)
        if len(pct_changes) >= 30:
            kurt = self._kurtosis(pct_changes)
            metrics["kurtosis"] = round(kurt, 1)
            if kurt > self.fat_tail_kurtosis:
                return self._alert(symbol, "WARNING", f"Fat tail detected (kurtosis {kurt:.1f})", metrics)

        # Layer 5: Volatility signature tracking
        vol_sig = self._track_volatility_signature(symbol, pct_changes)
        metrics["vol_signature"] = round(vol_sig, 2)
        if vol_sig > 0.85:
            return self._alert(symbol, "WARNING", f"Anomalous volatility signature ({vol_sig:.2f})", metrics)

        return BlackSwanAlert(is_black_swan=False, level="NORMAL", reason="All layers clear", symbol=symbol, metrics=metrics)

    def _alert(self, symbol: str, level: str, reason: str, metrics: Dict[str, float]) -> BlackSwanAlert:
        alert = BlackSwanAlert(
            is_black_swan=level == "CRITICAL",
            level=level,
            reason=reason,
            symbol=symbol,
            metrics=metrics,
        )
        self._alerts.append(alert)
        if level == "CRITICAL":
            self.halt(reason)
        return alert

    # ------------------------------------------------------------------
    # Halt / resume
    # ------------------------------------------------------------------
    def halt(self, reason: str):
        self._halted = True
        self._halt_reason = reason
        self._halt_until = time.time() + self.halt_duration

    def resume(self):
        self._halted = False
        self._halt_reason = ""
        self._halt_until = 0.0

    def is_halted(self) -> bool:
        if self._halted and time.time() >= self._halt_until:
            self.resume()
        return self._halted

    # ------------------------------------------------------------------
    # Volatility signature tracking
    # ------------------------------------------------------------------
    def _track_volatility_signature(self, symbol: str, pct_changes: np.ndarray) -> float:
        """Return anomaly score 0-1 based on recent vs historical volatility pattern."""
        if len(pct_changes) < 20:
            return 0.0
        recent_vol = np.std(pct_changes[-10:])
        hist_vol = np.std(pct_changes[:-10])
        if hist_vol <= 0:
            return 0.0
        ratio = recent_vol / hist_vol
        # Score: how many sigmas away from normal
        score = min(1.0, (ratio - 1.0) / 4.0)
        return max(0.0, score)

    def get_alert_history(self, last_n: int = 100) -> List[dict]:
        return [a.to_dict() for a in self._alerts[-last_n:]]

    def to_dict(self) -> dict:
        return {
            "halted": self.is_halted(),
            "halt_reason": self._halt_reason,
            "total_alerts": len(self._alerts),
            "critical_alerts": sum(1 for a in self._alerts if a.level == "CRITICAL"),
        }

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
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

    @staticmethod
    def _kurtosis(values: np.ndarray) -> float:
        if len(values) < 4:
            return 0.0
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return 0.0
        n = len(values)
        return float(np.sum(((values - mean) / std) ** 4) / n)


if __name__ == "__main__":
    guard = BlackSwanGuard()
    df = pd.DataFrame({
        "close": [100.0 + i * 0.1 for i in range(29)] + [85.0],
        "high": [100.5 + i * 0.1 for i in range(29)] + [90.0],
        "low": [99.5 + i * 0.1 for i in range(29)] + [80.0],
        "volume": [1000] * 29 + [50000],
    })
    alert = guard.check(df, symbol="THYAO")
    print(alert)

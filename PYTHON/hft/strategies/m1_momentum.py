"""
m1_momentum.py — 1-Minute Momentum Sniper strategy.
EMA 3/8 cross + volume spike. Hold 30-120 seconds.
"""

import numpy as np
from typing import Optional, Dict
from hft.config import HFTConfig
from hft.signal_generator import m1_momentum_signal


class M1MomentumStrategy:
    """
    M1 Momentum Sniper.
    Target: 0.3-1.0% profit per trade.
    Max hold: 120 seconds.
    """

    def __init__(self, config: Optional[HFTConfig] = None):
        self.config = config or HFTConfig(timeframe="1m")
        self.name = "M1_MOMENTUM"

    def analyze(self, bars: Dict[str, "pd.DataFrame"]) -> Dict[str, dict]:
        """
        Analyze all symbols and return signals.
        bars: {symbol: DataFrame with columns [timestamp, open, high, low, close, volume]}
        """
        import pandas as pd
        signals = {}
        for symbol, df in bars.items():
            if df is None or len(df) < 30:
                continue
            sig = self._analyze_single(df)
            if sig:
                signals[symbol] = sig
        return signals

    def _analyze_single(self, df: "pd.DataFrame") -> Optional[dict]:
        prices = df["close"].values
        volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        sig = m1_momentum_signal(
            prices=prices,
            volumes=volumes,
            ema_fast=3,
            ema_slow=8,
            volume_mult=self.config.volume_multiplier,
        )

        if sig == 0:
            return None

        last = df.iloc[-1]
        entry = last["close"]
        atr = self._atr(df["high"].values, df["low"].values, df["close"].values, period=14)

        sl = entry - atr * 2.0 if sig == 1 else entry + atr * 2.0
        tp1 = entry + atr * 3.0 if sig == 1 else entry - atr * 3.0
        tp2 = entry + atr * 4.0 if sig == 1 else entry - atr * 4.0

        r_r = abs(tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0

        return {
            "symbol": last.get("symbol", ""),
            "signal": sig,  # 1 = BUY, -1 = SELL
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "atr": atr,
            "r_r": r_r,
            "volume": last.get("volume", 0),
            "strategy": self.name,
        }

    @staticmethod
    def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """Average True Range."""
        if len(high) < period + 1:
            return np.mean(high - low) if len(high) > 0 else 0.0
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        return float(np.mean(tr[-period:]))

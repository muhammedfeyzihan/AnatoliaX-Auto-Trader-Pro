"""
s1_micro_scalp.py — 1-Second Micro Scalping strategy.
VWAP deviation + volume spike. Hold 3-15 seconds.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict
from hft.config import HFTConfig
from hft.signal_generator import s1_micro_scalp_signal


class S1MicroScalpStrategy:
    """
    S1 Micro Scalping.
    Target: 0.05-0.2% profit per trade.
    Max hold: 15 seconds.
    Only trades most liquid BIST30 symbols.
    """

    def __init__(self, config: Optional[HFTConfig] = None):
        self.config = config or HFTConfig(timeframe="1s")
        self.name = "S1_MICRO_SCALP"

    def analyze(self, bars: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
        signals = {}
        for symbol, df in bars.items():
            if df is None or len(df) < 30:
                continue
            sig = self._analyze_single(df)
            if sig:
                signals[symbol] = sig
        return signals

    def _analyze_single(self, df: pd.DataFrame) -> Optional[dict]:
        prices = df["close"].values
        volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        sig = s1_micro_scalp_signal(
            prices=prices,
            volumes=volumes,
            vwap_period=20,
            deviation_threshold=0.001,
        )

        if sig == 0:
            return None

        last = df.iloc[-1]
        entry = last["close"]
        # Tight SL/TP for S1
        sl = entry * 0.999 if sig == 1 else entry * 1.001
        tp = entry * 1.001 if sig == 1 else entry * 0.999

        return {
            "symbol": last.get("symbol", ""),
            "signal": sig,
            "entry": entry,
            "sl": sl,
            "tp1": tp,
            "tp2": tp * 1.002 if sig == 1 else tp * 0.998,
            "volume": last.get("volume", 0),
            "strategy": self.name,
        }

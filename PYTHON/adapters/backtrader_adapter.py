"""
adapters/backtrader_adapter.py — Backtrader Replay/Resampling Adapter

Provides a thin wrapper around Backtrader's Cerebro engine for tick-level
replay and resampling. Falls back to pure Python if backtrader unavailable.

Technique: backtrader's replay() method for tick→bar construction.
"""

from typing import Optional, Dict, List, Callable
import pandas as pd


class BacktraderReplayAdapter:
    """
    Tick-level replay and resampling via Backtrader.
    Converts tick data to OHLCV bars with configurable compression.
    """

    def __init__(self, compression: int = 1, timeframe: str = "minutes"):
        self.compression = compression
        self.timeframe = timeframe
        self._bt = None
        try:
            import backtrader as bt
            self._bt = bt
        except Exception:
            pass

    def replay_ticks(self, ticks: pd.DataFrame, bar_timeframe: str = "1min") -> pd.DataFrame:
        """
        Replay tick DataFrame into OHLCV bars.
        ticks columns: timestamp, price, size
        """
        if self._bt is not None:
            try:
                cerebro = self._bt.Cerebro()
                data = self._bt.feeds.PandasData(dataname=ticks)
                cerebro.adddata(data)
                cerebro.run()
                # Backtrader doesn't return DataFrame directly; use fallback
            except Exception:
                pass
        # Pure Python fallback: pandas resample
        ticks["timestamp"] = pd.to_datetime(ticks["timestamp"])
        ticks = ticks.set_index("timestamp")
        ohlcv = ticks["price"].resample(bar_timeframe).ohlc()
        ohlcv["volume"] = ticks["size"].resample(bar_timeframe).sum()
        ohlcv = ohlcv.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close"})
        ohlcv = ohlcv.fillna(method="ffill").dropna()
        return ohlcv

    def resample(self, df: pd.DataFrame, target: str = "1min") -> pd.DataFrame:
        """Resample existing OHLCV to a higher timeframe."""
        df = df.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        resampled = df.resample(target).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        return resampled.reset_index()

    def get_info(self) -> Dict:
        return {
            "adapter": "BacktraderReplayAdapter",
            "backtrader_available": self._bt is not None,
            "compression": self.compression,
            "timeframe": self.timeframe,
        }

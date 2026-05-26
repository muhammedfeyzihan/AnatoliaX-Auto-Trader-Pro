"""
tick_aggregator.py — Sub-minute bar aggregation from tick stream.
Inspired by Nautilus Trader's bar aggregation.
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional


class TickAggregator:
    """
    Aggregate incoming ticks into OHLCV bars of arbitrary intervals.
    Supports 1s, 5s, 10s, 30s, 1m, 5m.
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval = pd.Timedelta(seconds=interval_seconds)
        self._buffers: Dict[str, list] = defaultdict(list)
        self._bars: Dict[str, pd.DataFrame] = {}

    def ingest_tick(self, symbol: str, timestamp: datetime, price: float, size: float = 0.0):
        """Ingest a single tick."""
        self._buffers[symbol].append({
            "timestamp": timestamp,
            "price": price,
            "size": size,
        })

    def _align_bar_time(self, ts: datetime) -> datetime:
        """Align timestamp to bar boundary."""
        # Convert to pandas Timestamp for easy floor
        pts = pd.Timestamp(ts)
        floored = pts.floor(self.interval)
        return floored.to_pydatetime()

    def flush_bars(self) -> Dict[str, pd.DataFrame]:
        """
        Flush buffered ticks into bars and return new bars.
        Clears flushed ticks from buffers.
        """
        result = {}
        for symbol, ticks in self._buffers.items():
            if not ticks:
                continue

            df = pd.DataFrame(ticks)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["bar_time"] = df["timestamp"].apply(self._align_bar_time)

            bars = []
            for bar_time, group in df.groupby("bar_time"):
                bars.append({
                    "timestamp": bar_time,
                    "open": group["price"].iloc[0],
                    "high": group["price"].max(),
                    "low": group["price"].min(),
                    "close": group["price"].iloc[-1],
                    "volume": group["size"].sum(),
                    "tick_count": len(group),
                })

            if bars:
                bar_df = pd.DataFrame(bars).sort_values("timestamp").reset_index(drop=True)
                # Append to existing bars
                existing = self._bars.get(symbol)
                if existing is not None and not existing.empty:
                    combined = pd.concat([existing, bar_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
                    self._bars[symbol] = combined.reset_index(drop=True)
                else:
                    self._bars[symbol] = bar_df
                result[symbol] = bar_df

            # Clear flushed ticks
            self._buffers[symbol] = []

        return result

    def get_bars(self, symbol: str) -> pd.DataFrame:
        """Return all aggregated bars for a symbol."""
        return self._bars.get(symbol, pd.DataFrame())

    def get_latest_bar(self, symbol: str) -> Optional[pd.Series]:
        """Return the most recent completed bar."""
        df = self._bars.get(symbol)
        if df is None or df.empty:
            return None
        return df.iloc[-1]

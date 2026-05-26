"""
adapters/quantconnect_adapter.py — QuantConnect LEAN Time-Frontier Adapter

Wraps LEAN's time-frontier concept: no look-ahead bias via strict event-time
processing. Provides Python-side time-frontier validation compatible with
LEAN's algorithm framework.
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


class QuantConnectTimeFrontierAdapter:
    """
    LEAN-compatible time frontier to prevent look-ahead bias.
    All data access is gated by event_time <= frontier.
    """

    def __init__(self, warm_up_bars: int = 0):
        self.warm_up_bars = warm_up_bars
        self._frontier: Optional[datetime] = None
        self._history: List[Dict] = []
        self._violation_count = 0

    def set_frontier(self, timestamp: datetime):
        """Advance the time frontier. Monotonic only."""
        if self._frontier and timestamp < self._frontier:
            self._violation_count += 1
            return
        self._frontier = timestamp
        self._history.append({"frontier": timestamp, "wall_time": time.time()})

    def is_safe(self, data_timestamp: datetime) -> bool:
        """True if data_timestamp is at or before the current frontier."""
        if self._frontier is None:
            return False
        return data_timestamp <= self._frontier

    def gate_dataframe(self, df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
        """Filter DataFrame to only rows at or before frontier."""
        if self._frontier is None:
            return pd.DataFrame()
        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        return df[df[timestamp_col] <= self._frontier]

    def get_frontier(self) -> Optional[datetime]:
        return self._frontier

    def get_violations(self) -> int:
        return self._violation_count

    def get_info(self) -> Dict:
        return {
            "adapter": "QuantConnectTimeFrontierAdapter",
            "frontier": self._frontier.isoformat() if self._frontier else None,
            "violations": self._violation_count,
            "history_len": len(self._history),
        }

"""
adapters/marketstore_adapter.py — MarketStore Tick Archive Adapter

Provides read/write interface to MarketStore for tick-level OHLCV storage.
Falls back to Parquet/SQLite if MarketStore client (pymarketstore) unavailable.

Reference: https://github.com/alpacahq/marketstore
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


class MarketStoreAdapter:
    """
    MarketStore interface for tick and bar persistence.
    """

    def __init__(self, endpoint: str = "http://localhost:5993/rpc"):
        self.endpoint = endpoint
        self._client = None
        try:
            import pymarketstore as pymk
            self._client = pymk.Client(endpoint)
        except Exception:
            pass

    def write_ticks(self, symbol: str, df: pd.DataFrame) -> bool:
        """Write tick DataFrame to MarketStore. Falls back to Parquet."""
        if self._client is not None:
            try:
                self._client.write(
                    f"{symbol}/TICK/1Sec/OHLCV",  # bucket key
                    df.to_records(index=False)
                )
                return True
            except Exception:
                pass
        # Fallback: Parquet
        path = f"marketstore_fallback/{symbol}_ticks.parquet"
        df.to_parquet(path, index=False)
        return True

    def read_ticks(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Read ticks from MarketStore. Falls back to Parquet."""
        if self._client is not None:
            try:
                return self._client.query(
                    f"{symbol}/TICK/1Sec/OHLCV",
                    start=start,
                    end=end,
                )
            except Exception:
                pass
        # Fallback
        path = f"marketstore_fallback/{symbol}_ticks.parquet"
        try:
            df = pd.read_parquet(path)
            df = df[(df["timestamp"] >= start.isoformat()) & (df["timestamp"] <= end.isoformat())]
            return df
        except Exception:
            return pd.DataFrame()

    def get_info(self) -> Dict:
        return {
            "adapter": "MarketStoreAdapter",
            "endpoint": self.endpoint,
            "client_available": self._client is not None,
        }

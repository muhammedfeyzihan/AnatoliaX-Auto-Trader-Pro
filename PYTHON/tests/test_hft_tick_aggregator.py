"""
Test: PYTHON.hft.tick_aggregator
Sub-minute bar aggregation from tick stream.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.tick_aggregator import TickAggregator


class TestTickAggregator:
    def test_ingest_and_flush(self):
        agg = TickAggregator(interval_seconds=60)
        base = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            agg.ingest_tick("THYAO", base + pd.Timedelta(seconds=i), 100.0 + i, 100)
        bars = agg.flush_bars()
        assert "THYAO" in bars
        assert len(bars["THYAO"]) == 1
        bar = bars["THYAO"].iloc[0]
        assert bar["open"] == 100.0
        assert bar["close"] == 109.0
        assert bar["high"] == 109.0
        assert bar["low"] == 100.0
        assert bar["volume"] == 1000

    def test_multi_bar_flush(self):
        agg = TickAggregator(interval_seconds=60)
        base = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(130):
            agg.ingest_tick("THYAO", base + pd.Timedelta(seconds=i), 100.0 + i, 10)
        bars = agg.flush_bars()
        assert len(bars["THYAO"]) == 3  # 0-59, 60-119, 120-129

    def test_get_bars_returns_empty_for_unknown(self):
        agg = TickAggregator(interval_seconds=60)
        assert agg.get_bars("UNKNOWN").empty

    def test_latest_bar(self):
        agg = TickAggregator(interval_seconds=60)
        base = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            agg.ingest_tick("THYAO", base + pd.Timedelta(seconds=i), 100.0 + i, 100)
        agg.flush_bars()
        latest = agg.get_latest_bar("THYAO")
        assert latest is not None
        assert latest["close"] == 109.0

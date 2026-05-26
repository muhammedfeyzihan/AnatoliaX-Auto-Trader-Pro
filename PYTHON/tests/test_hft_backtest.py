"""
Test: PYTHON.hft.backtest.hft_backtest
Tick-level HFT backtest engine.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.backtest.hft_backtest import HFTBacktestEngine


class TestHFTBacktestEngine:
    def _make_ticks(self, n=300):
        base = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)
        return pd.DataFrame({
            "timestamp": [base + pd.Timedelta(seconds=i) for i in range(n)],
            "symbol": ["THYAO"] * n,
            "price": [100.0 + i * 0.1 for i in range(n)],
            "size": [100 + i * 10 for i in range(n)],
            "bid": [100.0 + i * 0.1 - 0.01 for i in range(n)],
            "ask": [100.0 + i * 0.1 + 0.01 for i in range(n)],
        })

    def test_run_returns_dict(self):
        ticks = self._make_ticks(300)
        eng = HFTBacktestEngine(ticks, strategy="m1_momentum", interval_seconds=60, initial_capital=100_000)
        result = eng.run()
        assert "trades" in result
        assert "equity" in result
        assert "final_capital" in result
        assert "latency_stats" in result
        assert "order_stats" in result

    def test_equity_curve_exists(self):
        ticks = self._make_ticks(300)
        eng = HFTBacktestEngine(ticks, strategy="m1_momentum", interval_seconds=60, initial_capital=100_000)
        result = eng.run()
        assert isinstance(result["equity"], pd.DataFrame)

    def test_order_stats(self):
        ticks = self._make_ticks(300)
        eng = HFTBacktestEngine(ticks, strategy="m1_momentum", interval_seconds=60, initial_capital=100_000)
        result = eng.run()
        stats = result["order_stats"]
        assert "total_orders" in stats

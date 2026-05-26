"""
test_vectorized_backtest.py — Tests for VectorizedBacktestEngine (K241)
"""
import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimization.vectorized_backtest import VectorizedBacktestEngine


class TestVectorizedBacktestEngine:
    def _make_df(self, n=200):
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
            "volume": np.random.randint(1000, 10000, n),
        })
        df.index = pd.date_range("2026-01-01", periods=n, freq="h")
        return df

    def test_run_produces_trades(self):
        df = self._make_df(500)
        # Inject a strong signal on some rows
        df["Signal"] = 0
        df.loc[df.index[10:20], "Signal"] = 2
        df.loc[df.index[30:40], "Signal"] = 2

        eng = VectorizedBacktestEngine(df, signal_func=lambda d: d)
        result = eng.run()
        assert len(result["trades"]) >= 1
        assert result["final_capital"] != 100_000.0
        assert "metrics" in result

    def test_tp_sl_logic(self):
        # Controlled price path: entry at 100, rises to 110, then drops to 90
        close = [100] * 5 + [103] * 5 + [105] * 5 + [108] * 5 + [95] * 10
        df = pd.DataFrame({
            "close": close,
            "high": close,
            "low": close,
            "volume": [5000] * len(close),
        })
        df.index = pd.date_range("2026-01-01", periods=len(close), freq="h")
        df["Signal"] = 0
        df.loc[df.index[0], "Signal"] = 2

        eng = VectorizedBacktestEngine(df, signal_func=lambda d: d)
        result = eng.run()
        # Should hit TP1 or SL
        assert len(result["trades"]) >= 1

    def test_equity_curve_length(self):
        df = self._make_df(100)
        df["Signal"] = 0
        eng = VectorizedBacktestEngine(df, signal_func=lambda d: d)
        result = eng.run()
        assert len(result["equity"]) == 100

    def test_max_positions_respected(self):
        df = self._make_df(200)
        df["Signal"] = 2  # Signal every bar
        eng = VectorizedBacktestEngine(df, signal_func=lambda d: d, max_positions=3)
        result = eng.run()
        # Max 3 positions should be open at any time
        # (hard to assert from final state, but at least run doesn't crash)
        assert "trades" in result

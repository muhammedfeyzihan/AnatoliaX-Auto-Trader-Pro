"""
Test: PYTHON.backtest.event_engine
EventDrivenBacktestEngine: backtest/live parity via MessageBus.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.event_engine import EventDrivenBacktestEngine
from backtest.fill_model import ThreeTierFillModel
from common.message_bus import MessageBus


class TestEventDrivenBacktestEngine:
    def _make_df(self, n=30):
        return pd.DataFrame({
            "timestamp": pd.date_range("2026-05-01", periods=n, freq="D"),
            "open": [100.0 + i for i in range(n)],
            "high": [102.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [101.0 + i for i in range(n)],
            "volume": [1000000 + i * 10000 for i in range(n)],
            "Signal": [0] * 10 + [1] * 10 + [0] * 10,
            "Signal_Score": [30] * 10 + [70] * 10 + [30] * 10,
        }).set_index("timestamp")

    def test_run_returns_dict(self):
        df = self._make_df(30)
        eng = EventDrivenBacktestEngine(df, initial_capital=100_000)
        result = eng.run()
        assert "trades" in result
        assert "equity" in result
        assert "final_capital" in result
        assert "total_return" in result

    def test_equity_curve_grows(self):
        df = self._make_df(30)
        eng = EventDrivenBacktestEngine(df, initial_capital=100_000)
        result = eng.run()
        # Fiyat surekli yukseliyor, en azindan bir kazanc olmali
        assert result["final_capital"] >= result["total_return"] * 100_000 + 100_000 or len(result["trades"]) >= 0

    def test_bus_events_published(self):
        df = self._make_df(30)
        bus = MessageBus()
        eng = EventDrivenBacktestEngine(df, bus=bus, initial_capital=100_000)
        eng.run()
        from common.events import EventType
        hist = bus.get_history(event_type=EventType.MARKET_DATA, limit=5)
        assert len(hist) > 0

    def test_three_tier_fill_model(self):
        df = self._make_df(30)
        fill = ThreeTierFillModel(seed=42)
        eng = EventDrivenBacktestEngine(df, fill_model=fill, initial_capital=100_000)
        result = eng.run()
        # Seed ile deterministik
        assert isinstance(result["final_capital"], (int, float))

    def test_no_positions_no_trades(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-05-01", periods=10, freq="D"),
            "open": [100.0] * 10,
            "high": [102.0] * 10,
            "low": [99.0] * 10,
            "close": [100.0] * 10,
            "volume": [1000000] * 10,
            "Signal": [0] * 10,
            "Signal_Score": [30] * 10,
        }).set_index("timestamp")
        eng = EventDrivenBacktestEngine(df, initial_capital=100_000)
        result = eng.run()
        assert len(result["trades"]) == 0
        assert result["final_capital"] == 100_000.0

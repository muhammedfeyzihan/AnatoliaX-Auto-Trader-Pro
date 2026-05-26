"""
Integration Test: End-to-End Flow
Sinyal > Risk kontrol > Execution > Paper broker
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.indicators import apply_all
from backtest.signals import combined_signal
from risk.kill_switch import KillSwitch
from risk.exposure_limiter import ExposureLimiter
from execution.engine import UnifiedExecutionEngine, OrderSide
from paper_trading.paper_broker import PaperBroker
from risk.database import init_db

init_db()


class TestEndToEndFlow:
    def _sample_df(self):
        return pd.DataFrame({
            "timestamp": pd.date_range("2026-05-01", periods=30, freq="D"),
            "open": [100.0 + i for i in range(30)],
            "high": [102.0 + i for i in range(30)],
            "low": [99.0 + i for i in range(30)],
            "close": [101.0 + i for i in range(30)],
            "volume": [1000000 + i * 10000 for i in range(30)],
        })

    def test_signal_to_execution(self):
        # 1. Sinyal uret
        df = self._sample_df()
        df = apply_all(df)
        df = combined_signal(df)
        last_signal = df.iloc[-1]["Signal"]
        assert last_signal in (0, 1, 2)

        # 2. Risk kontrol
        ks = KillSwitch(max_drawdown_pct=0.10)
        ks.update(capital=100000, daily_pnl=0)
        assert ks.is_alive() is True

        el = ExposureLimiter()
        result = el.check([], capital=100000)
        assert result["allowed"] is True

        # 3. Emir ver
        engine = UnifiedExecutionEngine(mode="backtest")
        order = engine.place_order("THYAO", OrderSide.BUY, 100, price=103.0)
        assert order.status.name == "FILLED"

        # 4. Paper broker kayit
        broker = PaperBroker(initial_capital=100000, max_positions=5)
        broker.setup_method = lambda: None  # Test icin temizlik bypass
        trade = broker.place_order("THYAO", "BUY", 100, 103.0)
        if trade:
            closed = broker.close_trade(trade.id, 110.0, reason="TP")
            assert closed is not None
            assert closed.status == "CLOSED"

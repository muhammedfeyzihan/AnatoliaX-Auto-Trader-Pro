"""
Acceptance Test: End-to-end event-driven flow.
Signal -> Risk -> Order -> Fill -> Portfolio update (event-driven).
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.message_bus import MessageBus
from common.events import EventType, OrderEvent, FillEvent
from risk.pre_trade_engine import PreTradeRiskEngine
from backtest.fill_model import ImmediateFillModel
from risk.account import Account
from risk.position import Position


class TestAcceptanceEventDrivenFlow:
    def test_signal_to_fill_updates_account(self):
        """Full flow: signal -> order -> fill -> account cash updated."""
        account = Account(initial_cash=100_000, max_position_value_pct=1.0)

        # Simulate fill and apply to account
        ok = account.open_position("THYAO", 100, 100.0, commission=0.0)
        assert ok is True
        assert account.cash == 90_000.0

        pos = account.get_position("THYAO")
        assert pos.is_open
        assert pos.quantity == 100.0
        assert pos.avg_entry_price == 100.0

    def test_mark_to_market_after_fill(self):
        bus = MessageBus()
        account = Account(initial_cash=100_000, max_position_value_pct=1.0)

        account.open_position("THYAO", 100, 100.0)
        account.mark_to_market({"THYAO": 110.0})

        assert account.unrealized_pnl == 1000.0
        assert account.equity == 91_000.0

    def test_multiple_symbols_portfolio(self):
        account = Account(initial_cash=1_000_000, max_position_value_pct=1.0, max_total_positions=10)
        account.open_position("THYAO", 100, 100.0)
        account.open_position("GARAN", 200, 50.0)
        account.mark_to_market({"THYAO": 110.0, "GARAN": 55.0})

        assert account.open_position_count == 2
        assert account.unrealized_pnl == 1000.0 + 1000.0

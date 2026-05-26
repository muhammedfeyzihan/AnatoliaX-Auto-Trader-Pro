"""
Test: PYTHON.hft.position_manager
HFT position lifecycle, SL/TP, inventory skew.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.account import Account
from hft.position_manager import HFTPositionManager


class TestHFTPositionManager:
    def test_enter_and_exit(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        ok = pm.enter_position("THYAO", 100, 100.0, commission=10.0)
        assert ok is True
        assert acc.open_position_count == 1

        pnl = pm.exit_position("THYAO", 100, 110.0, commission=10.0)
        # Entry commission tracked but not deducted from realized_pnl (only exit commission is)
        assert pnl == 1000.0 - 10.0
        assert acc.open_position_count == 0

    def test_inventory_skew(self):
        acc = Account(initial_cash=1_000_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        pm.enter_position("THYAO", 1000, 100.0)
        pm.enter_position("GARAN", 100, 50.0)
        skew = pm.get_inventory_skew()
        assert 0.0 < skew <= 1.0

    def test_can_exit_sl(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        pm.enter_position("THYAO", 100, 100.0)
        should, reason = pm.can_exit("THYAO", 99.0, sl_pct=0.01, tp_pct=0.02)
        assert should is True
        assert reason == "SL"

    def test_can_exit_tp(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        pm.enter_position("THYAO", 100, 100.0)
        should, reason = pm.can_exit("THYAO", 103.0, sl_pct=0.01, tp_pct=0.02)
        assert should is True
        assert reason == "TP"

    def test_can_exit_hold(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        pm.enter_position("THYAO", 100, 100.0)
        should, reason = pm.can_exit("THYAO", 100.5, sl_pct=0.01, tp_pct=0.02)
        assert should is False
        assert reason == "HOLD"

    def test_holding_time(self):
        acc = Account(initial_cash=100_000, max_position_value_pct=1.0)
        pm = HFTPositionManager(acc)
        pm.enter_position("THYAO", 100, 100.0)
        import time
        time.sleep(0.05)
        ht = pm.holding_time_seconds("THYAO")
        assert ht >= 0.04

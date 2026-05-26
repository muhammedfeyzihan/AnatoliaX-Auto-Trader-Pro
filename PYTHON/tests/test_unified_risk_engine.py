"""
test_unified_risk_engine.py — Tests for UnifiedRiskEngine (K204-K210)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.unified_risk_engine import UnifiedRiskEngine, RiskCheckResult


class TestUnifiedRiskEngine:
    def test_default_initialization(self):
        engine = UnifiedRiskEngine()
        assert engine.max_daily_dd == 0.05
        assert engine.max_concurrent_positions == 10
        assert engine.max_single_exposure == 0.02
        assert engine.max_total_exposure == 0.10
        assert engine.max_sector_exposure == 0.20
        assert engine.max_heat == 0.25
        assert engine.consecutive_losses_limit == 3
        assert engine.kelly_fraction == 0.25

    def test_custom_limits(self):
        engine = UnifiedRiskEngine(
            max_daily_dd=0.03,
            max_concurrent_positions=5,
            max_single_exposure=0.01,
            max_total_exposure=0.05,
            max_sector_exposure=0.10,
            max_heat=0.15,
            consecutive_losses_limit=2,
            kelly_fraction=0.20,
        )
        assert engine.max_daily_dd == 0.03
        assert engine.max_concurrent_positions == 5

    def test_kill_switch_drawdown(self):
        engine = UnifiedRiskEngine(max_daily_dd=0.05)
        engine.update_capital(capital=100000, daily_pnl=0)
        result = engine.check()
        assert result.allowed is True

        engine.update_capital(capital=94000, daily_pnl=-6000)
        result = engine.check()
        assert result.allowed is False
        assert result.kill_switch_triggered is True
        assert any("KILL_SWITCH" in a for a in result.alerts)

    def test_concurrent_positions_limit(self):
        engine = UnifiedRiskEngine(max_concurrent_positions=2)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 100, "price": 150},
            {"symbol": "GARAN", "size": 100, "price": 80},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("MAX_POSITIONS" in a for a in result.alerts)

    def test_single_exposure_limit(self):
        engine = UnifiedRiskEngine(max_single_exposure=0.02)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 1000, "price": 300},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("SINGLE_EXPOSURE" in a for a in result.alerts)

    def test_total_exposure_limit(self):
        engine = UnifiedRiskEngine(max_total_exposure=0.10)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 500, "price": 100},
            {"symbol": "GARAN", "size": 500, "price": 100},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("TOTAL_EXPOSURE" in a for a in result.alerts)

    def test_sector_exposure_limit(self):
        engine = UnifiedRiskEngine(max_sector_exposure=0.20)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 300, "price": 100, "sector": "HAVACILIK"},
            {"symbol": "PGSUS", "size": 300, "price": 100, "sector": "HAVACILIK"},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("SECTOR_EXPOSURE" in a for a in result.alerts)

    def test_signal_exposure_check(self):
        engine = UnifiedRiskEngine(max_single_exposure=0.02, max_total_exposure=0.10)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 100, "price": 100},
        ])
        signal = {"symbol": "GARAN", "size": 5000, "price": 100, "sector": "BANKA"}
        result = engine.check(signal=signal)
        assert result.allowed is False
        assert any("SIGNAL_EXPOSURE" in a for a in result.alerts)

    def test_portfolio_heat(self):
        engine = UnifiedRiskEngine(max_heat=0.25)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "entry_price": 100, "stop_loss": 95, "size": 1000},
        ])
        result = engine.check()
        # heat = (100-95)*1000 / 100000 = 0.05
        assert result.allowed is True
        assert result.position_scale == 1.0

    def test_high_heat_scaling(self):
        engine = UnifiedRiskEngine(max_heat=0.01)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "entry_price": 100, "stop_loss": 95, "size": 1000},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("HEAT" in a for a in result.alerts)
        assert result.position_scale == 0.5

    def test_consecutive_losses_cooldown(self):
        engine = UnifiedRiskEngine(consecutive_losses_limit=3)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.update_trade(pnl=-100)
        engine.update_trade(pnl=-100)
        result = engine.check()
        assert result.allowed is True
        engine.update_trade(pnl=-100)
        result = engine.check()
        assert result.allowed is False
        assert any("CONSECUTIVE_LOSSES" in a for a in result.alerts)
        assert result.position_scale == 0.25

    def test_drawdown_scaling(self):
        engine = UnifiedRiskEngine(max_daily_dd=0.10)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.update_capital(capital=96000, daily_pnl=-4000)
        result = engine.check()
        # dd=0.04 >= 0.10*0.5=0.05? No, 0.04 < 0.05
        assert result.position_scale == 1.0

        engine.update_capital(capital=94000, daily_pnl=-6000)
        result = engine.check()
        # dd=0.06 >= 0.05
        assert result.position_scale == 0.5
        assert any("DD_WARNING" in a for a in result.alerts)

    def test_dynamic_sl_multiplier(self):
        engine = UnifiedRiskEngine(max_daily_dd=0.10)
        engine.update_capital(capital=100000, daily_pnl=0)
        result = engine.check()
        assert result.dynamic_sl_multiplier == 1.0

        engine.update_capital(capital=94000, daily_pnl=-6000)
        result = engine.check()
        assert result.dynamic_sl_multiplier == 0.75

    def test_kill_switch_callback(self):
        triggered = []

        def on_kill(reason):
            triggered.append(reason)

        engine = UnifiedRiskEngine(max_daily_dd=0.05, on_kill_switch=on_kill)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.update_capital(capital=94000, daily_pnl=-6000)
        engine.check()
        assert len(triggered) == 1
        assert "KILL_SWITCH" in triggered[0]

    def test_update_trade_resets_win_streak(self):
        engine = UnifiedRiskEngine()
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.update_trade(pnl=-100)
        engine.update_trade(pnl=-100)
        engine.update_trade(pnl=50)
        result = engine.check()
        assert result.allowed is True
        assert engine._loss_streak == 0

    def test_add_remove_position(self):
        engine = UnifiedRiskEngine()
        engine.add_position({"symbol": "THYAO", "size": 100, "price": 150})
        assert len(engine._positions) == 1
        engine.remove_position("THYAO")
        assert len(engine._positions) == 0

    def test_reset(self):
        engine = UnifiedRiskEngine(max_daily_dd=0.05)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.update_capital(capital=94000, daily_pnl=-6000)
        engine.check()
        assert engine._kill_switch_triggered is True
        engine.reset()
        assert engine._kill_switch_triggered is False
        assert engine._daily_pnl == 0.0
        assert engine._loss_streak == 0

    def test_disarm(self):
        engine = UnifiedRiskEngine()
        assert engine.is_alive() is True
        engine.disarm()
        assert engine.is_alive() is False

    def test_get_status(self):
        engine = UnifiedRiskEngine()
        engine.update_capital(capital=100000, daily_pnl=0)
        status = engine.get_status()
        assert status["capital"] == 100000
        assert status["drawdown"] == 0.0
        assert status["positions"] == 0

    def test_empty_positions_no_exposure(self):
        engine = UnifiedRiskEngine()
        engine.update_capital(capital=100000, daily_pnl=0)
        result = engine.check()
        assert result.allowed is True
        assert result.reason == "OK"

    def test_zero_capital_drawdown(self):
        engine = UnifiedRiskEngine()
        engine.update_capital(capital=0, daily_pnl=0)
        dd = engine._calculate_drawdown()
        assert dd == 0.0

    def test_position_with_value_field(self):
        engine = UnifiedRiskEngine(max_single_exposure=0.02)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "value": 5000},
        ])
        result = engine.check()
        assert result.allowed is False
        assert any("SINGLE_EXPOSURE" in a for a in result.alerts)

    def test_heat_with_missing_sl(self):
        engine = UnifiedRiskEngine()
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "entry_price": 100, "size": 100},
        ])
        heat = engine._check_heat()
        # sl defaults to entry * 0.95 = 95, heat = (100-95)*100/100000 = 0.005
        assert heat["heat"] == 0.005

    def test_signal_without_symbol(self):
        engine = UnifiedRiskEngine(max_total_exposure=0.10)
        engine.update_capital(capital=100000, daily_pnl=0)
        signal = {"size": 5000, "price": 100}
        result = engine.check(signal=signal)
        assert result.allowed is False
        assert any("TOTAL_EXPOSURE" in a for a in result.alerts)

    def test_alerts_reason_format(self):
        engine = UnifiedRiskEngine(max_concurrent_positions=0, max_single_exposure=0.01)
        engine.update_capital(capital=100000, daily_pnl=0)
        engine.set_positions([
            {"symbol": "THYAO", "size": 500, "price": 100},
        ])
        result = engine.check()
        assert result.reason != ""
        assert result.reason != "OK"
        assert ";" in result.reason

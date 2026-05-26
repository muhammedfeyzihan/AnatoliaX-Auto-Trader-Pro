"""
Test: PYTHON.risk.kill_switch, volatility_throttle, exposure_limiter, portfolio_heat
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.kill_switch import KillSwitch, CircuitBreaker
from risk.volatility_throttle import VolatilityThrottle
from risk.exposure_limiter import ExposureLimiter
from risk.portfolio_heat import PortfolioHeat


class TestKillSwitch:
    def test_drawdown_trigger(self):
        ks = KillSwitch(max_drawdown_pct=0.05)
        ks.update(capital=100000, daily_pnl=0)
        assert ks.is_alive() is True
        ks.update(capital=94000, daily_pnl=0)
        assert ks.is_alive() is False
        assert "Max Drawdown" in ks.get_alerts()[0]

    def test_daily_loss_trigger(self):
        ks = KillSwitch(daily_loss_pct=0.02)
        ks.update(capital=100000, daily_pnl=-2500)
        assert ks.is_alive() is False

    def test_consecutive_losses(self):
        ks = KillSwitch(consecutive_losses=3)
        ks.update(capital=100000, daily_pnl=0, last_trade_pnl=-100)
        ks.update(capital=100000, daily_pnl=0, last_trade_pnl=-100)
        ks.update(capital=100000, daily_pnl=0, last_trade_pnl=-100)
        assert ks.is_alive() is False

    def test_reset(self):
        ks = KillSwitch(max_drawdown_pct=0.05)
        ks.update(capital=100000, daily_pnl=0)
        ks.update(capital=94000, daily_pnl=0)
        assert ks.is_alive() is False
        ks.reset()
        assert ks.is_alive() is True


class TestCircuitBreaker:
    def test_open_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_sec=0.01)

        def fail():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError, match="fail"):
            cb.call(fail)
        with pytest.raises(RuntimeError, match="fail"):
            cb.call(fail)
        with pytest.raises(RuntimeError, match="OPEN"):
            cb.call(fail)

        import time
        time.sleep(0.05)
        assert cb.is_open() is False


class TestVolatilityThrottle:
    def test_high_vol_reduces_size(self):
        vt = VolatilityThrottle(high_vol_threshold=0.03)
        size = vt.throttle(size=100, atr=5.0, price=100.0)
        assert size < 100

    def test_low_vol_full_size(self):
        vt = VolatilityThrottle(high_vol_threshold=0.03)
        size = vt.throttle(size=100, atr=0.01, price=100.0)
        assert size == 100

    def test_is_trading_allowed(self):
        vt = VolatilityThrottle(high_vol_threshold=0.03)
        assert vt.is_trading_allowed(atr=1.0, price=100.0) is True
        assert vt.is_trading_allowed(atr=5.0, price=100.0) is False


class TestExposureLimiter:
    def test_single_position_limit(self):
        el = ExposureLimiter(max_single_position_pct=0.02)
        positions = [{"symbol": "THYAO", "size": 100, "price": 3000.0}]
        result = el.check(positions, capital=100000)
        assert result["allowed"] is False
        assert any("POSITION_LIMIT" in a for a in result["alerts"])

    def test_total_exposure_limit(self):
        el = ExposureLimiter(max_total_exposure_pct=0.10)
        positions = [
            {"symbol": "THYAO", "size": 100, "price": 500.0},
            {"symbol": "GARAN", "size": 100, "price": 600.0},
        ]
        result = el.check(positions, capital=100000)
        assert result["allowed"] is False
        assert any("TOTAL_EXPOSURE" in a for a in result["alerts"])


class TestPortfolioHeat:
    def test_heat_calculation(self):
        ph = PortfolioHeat(max_heat=0.25)
        positions = [
            {"symbol": "THYAO", "entry_price": 100, "stop_loss": 95, "size": 100},
        ]
        result = ph.calculate_heat(positions, capital=100000)
        assert result["heat"] > 0
        assert result["allowed"] is True

    def test_correlation_risk(self):
        ph = PortfolioHeat()
        df = pd.DataFrame({
            "THYAO": [0.01, -0.02, 0.01, 0.03, -0.01],
            "GARAN": [0.01, -0.02, 0.01, 0.03, -0.01],
        })
        result = ph.correlation_risk(df)
        assert result["max_correlation"] > 0.90
        assert len(result["alerts"]) > 0

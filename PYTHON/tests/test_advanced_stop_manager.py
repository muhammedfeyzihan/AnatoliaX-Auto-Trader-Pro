"""
Test: PYTHON.risk.advanced_stop_manager
TrailingStop, ChandelierExit, ParabolicSARStop, TimeBasedExit, VolatilityBasedStop, CompositeStopManager.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.advanced_stop_manager import (
    TrailingStop,
    ChandelierExit,
    ParabolicSARStop,
    TimeBasedExit,
    VolatilityBasedStop,
    CompositeStopManager,
)


class TestTrailingStop:
    def test_buy_atr_initial_sl(self):
        ts = TrailingStop(entry=100.0, atr=2.5, multiplier=2.0, side="BUY", step_type="atr")
        assert ts.current_sl == 95.0  # 100 - (2.5*2)

    def test_sell_atr_initial_sl(self):
        ts = TrailingStop(entry=100.0, atr=2.5, multiplier=2.0, side="SELL", step_type="atr")
        assert ts.current_sl == 105.0

    def test_buy_price_step_update(self):
        ts = TrailingStop(entry=100.0, initial_stop=95.0, side="BUY", step_type="price")
        sl = ts.update(105.0)
        assert sl > 95.0  # SL yukari cekildi
        assert not ts.is_triggered()

    def test_buy_triggered(self):
        ts = TrailingStop(entry=100.0, initial_stop=95.0, side="BUY", step_type="atr")
        ts.update(94.0)
        assert ts.is_triggered()

    def test_sell_triggered(self):
        ts = TrailingStop(entry=100.0, initial_stop=105.0, side="SELL", step_type="atr")
        ts.update(106.0)
        assert ts.is_triggered()

    def test_update_history(self):
        ts = TrailingStop(entry=100.0, initial_stop=95.0, side="BUY", step_type="atr")
        ts.update(102.0)
        assert len(ts.history) == 2

    def test_summary_keys(self):
        ts = TrailingStop(entry=100.0, initial_stop=95.0, side="BUY", step_type="atr")
        s = ts.summary()
        assert "entry" in s
        assert "current_sl" in s
        assert "triggered" in s

    def test_invalid_without_atr_or_initial(self):
        with pytest.raises(ValueError):
            TrailingStop(entry=100.0, side="BUY")

    def test_triggered_idempotent(self):
        ts = TrailingStop(entry=100.0, initial_stop=95.0, side="BUY", step_type="atr")
        ts.update(94.0)
        sl = ts.update(90.0)
        assert ts.is_triggered()
        assert sl == ts.current_sl


class TestChandelierExit:
    def _sample_df(self):
        idx = pd.date_range("2026-05-01", periods=30)
        high = pd.Series(np.linspace(100, 130, 30) + np.random.rand(30) * 2, index=idx)
        low = high - np.random.rand(30) * 5
        close = (high + low) / 2
        return high, low, close

    def test_calculate_columns(self):
        h, l, c = self._sample_df()
        ce = ChandelierExit(h, l, c, period=10, atr_period=10, multiplier=3.0)
        df = ce.calculate()
        assert set(df.columns) == {"long_stop", "short_stop", "direction"}

    def test_direction_values(self):
        h, l, c = self._sample_df()
        ce = ChandelierExit(h, l, c, period=10, atr_period=10, multiplier=3.0)
        df = ce.calculate()
        assert set(df["direction"].unique()).issubset({1, -1})

    def test_long_stop_below_high(self):
        h, l, c = self._sample_df()
        ce = ChandelierExit(h, l, c, period=10, atr_period=10, multiplier=3.0)
        df = ce.calculate()
        assert (df["long_stop"] <= h).all()


class TestParabolicSARStop:
    def _sample_df(self):
        idx = pd.date_range("2026-05-01", periods=30)
        high = pd.Series(np.linspace(100, 130, 30) + np.random.rand(30) * 2, index=idx)
        low = high - np.random.rand(30) * 5
        return high, low

    def test_calculate_columns(self):
        h, l = self._sample_df()
        psar = ParabolicSARStop(h, l)
        df = psar.calculate()
        assert set(df.columns) == {"psar", "trend"}

    def test_trend_values(self):
        h, l = self._sample_df()
        psar = ParabolicSARStop(h, l)
        df = psar.calculate()
        assert set(df["trend"].unique()).issubset({1, -1})


class TestTimeBasedExit:
    def test_days_triggered(self):
        te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20"), max_days=5)
        assert te.update(pd.Timestamp("2026-05-25")) is True

    def test_days_not_triggered(self):
        te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20"), max_days=5)
        assert te.update(pd.Timestamp("2026-05-22")) is False

    def test_bars_triggered(self):
        te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20"), max_bars=3)
        te.update(pd.Timestamp("2026-05-20 09:30"))
        te.update(pd.Timestamp("2026-05-20 09:45"))
        te.update(pd.Timestamp("2026-05-20 10:00"))
        assert te.update(pd.Timestamp("2026-05-20 10:15")) is True

    def test_remaining_bars(self):
        te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20"), max_bars=5)
        te.update(pd.Timestamp("2026-05-20 09:30"))
        assert te.remaining_bars() == 4

    def test_remaining_days(self):
        te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20"), max_days=5)
        assert pytest.approx(te.remaining_days(pd.Timestamp("2026-05-22")), abs=1e-6) == 3.0


class TestVolatilityBasedStop:
    def test_buy_normal(self):
        vs = VolatilityBasedStop(entry=100.0, base_sl_pct=2.0, atr=2.0, atr_ema=2.0, side="BUY")
        sl = vs.calculate()
        assert pytest.approx(sl, abs=0.01) == 98.0

    def test_sell_normal(self):
        vs = VolatilityBasedStop(entry=100.0, base_sl_pct=2.0, atr=2.0, atr_ema=2.0, side="SELL")
        sl = vs.calculate()
        assert pytest.approx(sl, abs=0.01) == 102.0

    def test_high_vol_expand(self):
        vs = VolatilityBasedStop(entry=100.0, base_sl_pct=2.0, atr=3.0, atr_ema=2.0, expand_factor=1.5, side="BUY")
        sl = vs.calculate()
        assert pytest.approx(sl, abs=0.01) == 97.0  # 2% * 1.5 = 3%

    def test_low_vol_contract(self):
        vs = VolatilityBasedStop(entry=100.0, base_sl_pct=2.0, atr=1.0, atr_ema=2.0, contract_factor=0.75, side="BUY")
        sl = vs.calculate()
        assert pytest.approx(sl, abs=0.01) == 98.5  # 2% * 0.75 = 1.5%

    def test_gap_adjust(self):
        vs = VolatilityBasedStop(entry=100.0, base_sl_pct=2.0, side="BUY")
        sl = vs.adjust_for_gap(1.5)
        assert pytest.approx(sl, abs=0.01) == 96.5  # 2% + 1.5% = 3.5%


class TestCompositeStopManager:
    def test_add_and_update_trailing(self):
        mgr = CompositeStopManager()
        mgr.add_trailing_stop("ord1", entry=100.0, initial_stop=95.0, side="BUY")
        r = mgr.update("ord1", 96.0)
        assert r["action"] == "HOLD"
        r = mgr.update("ord1", 94.0)
        assert r["action"] == "CLOSE"
        assert "Trailing stop triggered" in r["reason"]

    def test_add_and_update_time(self):
        mgr = CompositeStopManager()
        mgr.add_time_exit("ord2", entry_time=pd.Timestamp("2026-05-20"), max_days=1)
        r = mgr.update("ord2", 100.0, current_time=pd.Timestamp("2026-05-21"))
        assert r["action"] == "CLOSE"

    def test_remove(self):
        mgr = CompositeStopManager()
        mgr.add_trailing_stop("ord3", entry=100.0, initial_stop=95.0, side="BUY")
        assert mgr.remove("ord3") is True
        assert mgr.remove("ord3") is False

    def test_list_active(self):
        mgr = CompositeStopManager()
        mgr.add_trailing_stop("ord4", entry=100.0, initial_stop=95.0, side="BUY")
        assert "ord4" in mgr.list_active()

    def test_unknown_order_id(self):
        mgr = CompositeStopManager()
        r = mgr.update("nonexistent", 100.0)
        assert r["action"] == "HOLD"
        assert "No stop registered" in r["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

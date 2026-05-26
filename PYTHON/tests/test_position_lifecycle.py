"""
test_position_lifecycle.py — Tests for PositionLifecycleManager (K215-K218)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.position_lifecycle import (
    PositionLifecycleManager, PositionLifecycleState, LifecycleStage
)


class TestPositionLifecycleManager:
    def test_open_position(self):
        mgr = PositionLifecycleManager()
        pos = mgr.open_position("THYAO", "long", 100, 150.0)
        assert pos.symbol == "THYAO"
        assert pos.stage == LifecycleStage.OPEN
        assert pos.size == 100

    def test_breakeven_trigger(self):
        mgr = PositionLifecycleManager(breakeven_pct=0.05, tp1_pct=0.10, tp2_pct=0.15, tp3_pct=0.20)
        mgr.open_position("THYAO", "long", 100, 100.0)
        result = mgr.update_price("THYAO", 106.0)
        assert result["stage"] == LifecycleStage.BREAKEVEN.value
        assert any(a["action"] == "MOVE_SL_BREAKEVEN" for a in result["actions"])

    def test_partial_tp1(self):
        mgr = PositionLifecycleManager(tp1_pct=0.03)
        mgr.open_position("THYAO", "long", 100, 100.0)
        result = mgr.update_price("THYAO", 103.0)
        assert any(a["action"] == "PARTIAL_TP1" for a in result["actions"])
        pos = mgr.get_position("THYAO")
        assert pos.partials_taken == 1
        assert pos.size == 75  # 100 - 25%

    def test_trailing_activation(self):
        mgr = PositionLifecycleManager(
            tp1_pct=0.03, tp2_pct=0.05, tp3_pct=0.08,
            trailing_activation_pct=0.10, trailing_step_pct=0.02
        )
        mgr.open_position("THYAO", "long", 100, 100.0)
        mgr.update_price("THYAO", 103.0)
        mgr.update_price("THYAO", 105.0)
        result = mgr.update_price("THYAO", 110.0)
        assert result["stage"] == LifecycleStage.TRAILING.value
        assert any(a["action"] == "TRAILING_START" for a in result["actions"])

    def test_trailing_update(self):
        mgr = PositionLifecycleManager(
            tp1_pct=0.03, tp2_pct=0.05, tp3_pct=0.08,
            trailing_activation_pct=0.10, trailing_step_pct=0.02
        )
        mgr.open_position("THYAO", "long", 100, 100.0)
        mgr.update_price("THYAO", 110.0)
        result = mgr.update_price("THYAO", 112.0)
        assert any(a["action"] == "TRAILING_UPDATE" for a in result["actions"])

    def test_close_on_stop(self):
        mgr = PositionLifecycleManager(
            tp1_pct=0.03, tp2_pct=0.05, tp3_pct=0.08,
            trailing_activation_pct=0.10, trailing_step_pct=0.02
        )
        mgr.open_position("THYAO", "long", 100, 100.0)
        mgr.update_price("THYAO", 110.0)
        # Drop below trailing stop
        result = mgr.update_price("THYAO", 107.0)
        # Should trigger close
        assert mgr.get_position("THYAO") is None

    def test_pyramiding(self):
        mgr = PositionLifecycleManager(pyramiding_max=2)
        mgr.open_position("THYAO", "long", 100, 100.0)
        pos = mgr.pyramid("THYAO", 50, 105.0)
        assert pos.size == 150
        assert pos.entry_price == pytest.approx(101.666, rel=0.01)

    def test_pyramiding_limit(self):
        mgr = PositionLifecycleManager(pyramiding_max=0)
        mgr.open_position("THYAO", "long", 100, 100.0)
        mgr.update_price("THYAO", 103.0)
        pos = mgr.pyramid("THYAO", 50, 105.0)
        # Already took partial, pyramid limited
        assert pos.size == 75

    def test_short_position(self):
        mgr = PositionLifecycleManager()
        mgr.open_position("THYAO", "short", 100, 100.0)
        result = mgr.update_price("THYAO", 94.0)
        assert result["pnl_pct"] == 0.06
        assert any(a["action"] == "MOVE_SL_BREAKEVEN" for a in result["actions"])

    def test_short_trailing(self):
        mgr = PositionLifecycleManager(
            trailing_activation_pct=0.10, trailing_step_pct=0.02
        )
        mgr.open_position("THYAO", "short", 100, 100.0)
        mgr.update_price("THYAO", 90.0)
        result = mgr.update_price("THYAO", 88.0)
        assert any(a["action"] == "TRAILING_UPDATE" for a in result["actions"])

    def test_close_position(self):
        mgr = PositionLifecycleManager()
        mgr.open_position("THYAO", "long", 100, 100.0)
        pos = mgr.close_position("THYAO", 110.0)
        assert pos.stage == LifecycleStage.CLOSED
        assert pos.realized_pnl == 1000.0

    def test_events_callback(self):
        events = []

        def on_event(event_type, pos):
            events.append(event_type)

        mgr = PositionLifecycleManager(on_event=on_event)
        mgr.open_position("THYAO", "long", 100, 100.0)
        assert "OPEN" in events

    def test_reset(self):
        mgr = PositionLifecycleManager()
        mgr.open_position("THYAO", "long", 100, 100.0)
        mgr.reset()
        assert mgr.get_position("THYAO") is None

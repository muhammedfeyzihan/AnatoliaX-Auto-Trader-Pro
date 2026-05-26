"""
test_time_rules.py — TimeBasedTradingManager tests (K246-K248)
"""

import pytest
from datetime import datetime, time, timedelta, timezone

from common.time_rules import (
    TimeBasedTradingManager,
    TradingWindow,
    TimeAlertLevel,
    WindowConfig,
)


class TestWindowDetection:
    def test_pre_market_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.PRE_MARKET

    def test_opening_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.OPENING

    def test_morning_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.MORNING

    def test_lunch_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.LUNCH

    def test_afternoon_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.AFTERNOON

    def test_closing_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.CLOSING

    def test_post_market_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 20, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.POST_MARKET

    def test_night_window(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 3, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.NIGHT

    def test_boundary_start(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 30, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.OPENING

    def test_boundary_end(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 11, 30, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.LUNCH


class TestTradingPermissions:
    def test_can_trade_morning(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is True

    def test_cannot_trade_lunch(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is False

    def test_cannot_trade_pre_market(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is False

    def test_cannot_trade_night(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 3, 0, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is False

    def test_can_trade_afternoon(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is True

    def test_can_trade_closing(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        assert tm.can_trade_now(dt) is True


class TestRiskMultipliers:
    def test_opening_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 1.2

    def test_morning_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 1.0

    def test_lunch_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 0.5

    def test_closing_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 0.7

    def test_pre_market_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 0.0

    def test_night_risk_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 3, 0, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 0.0


class TestPositionSizing:
    def test_opening_sl_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        assert tm.get_sl_multiplier(dt) == 1.5

    def test_closing_sl_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        assert tm.get_sl_multiplier(dt) == 0.8

    def test_default_sl_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc)
        assert tm.get_sl_multiplier(dt) == 1.0

    def test_opening_tp_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        assert tm.get_tp_multiplier(dt) == 1.2

    def test_lunch_tp_multiplier(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert tm.get_tp_multiplier(dt) == 0.8

    def test_opening_max_positions(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        assert tm.get_max_positions(dt) == 3

    def test_morning_max_positions(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.get_max_positions(dt) == 5

    def test_closing_max_positions(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        assert tm.get_max_positions(dt) == 2

    def test_lunch_max_positions(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert tm.get_max_positions(dt) == 2


class TestAlerts:
    def test_lunch_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 2
        assert any(a.level == TimeAlertLevel.BLOCK for a in alerts)
        assert any(a.level == TimeAlertLevel.WARNING and "Ogle arasi" in a.message for a in alerts)

    def test_closing_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 1
        assert alerts[0].level == TimeAlertLevel.WARNING
        assert "Kapanis oncesi" in alerts[0].message

    def test_opening_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 9, 45, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 1
        assert alerts[0].level == TimeAlertLevel.INFO
        assert "Acilis momentumu" in alerts[0].message

    def test_morning_no_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 0

    def test_afternoon_no_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 0

    def test_pre_market_block_alert(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc)
        alerts = tm.check_and_alert(dt)
        assert len(alerts) == 1
        assert alerts[0].level == TimeAlertLevel.BLOCK

    def test_alert_callback(self):
        tm = TimeBasedTradingManager()
        received = []
        def cb(alert):
            received.append(alert)
        tm.add_alert_callback(cb)
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        tm.check_and_alert(dt)
        assert len(received) == 2

    def test_get_alerts_filtered(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        tm.check_and_alert(dt)
        blocks = tm.get_alerts(TimeAlertLevel.BLOCK)
        assert len(blocks) == 1
        warnings = tm.get_alerts(TimeAlertLevel.WARNING)
        assert len(warnings) == 1

    def test_clear_alerts(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        tm.check_and_alert(dt)
        assert len(tm.get_alerts()) > 0
        tm.clear_alerts()
        assert len(tm.get_alerts()) == 0


class TestOptimalTradingSuggestion:
    def test_can_trade_now_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is True
        assert suggestion["minutes_until"] == 0
        assert suggestion["current_window"] == "morning"

    def test_lunch_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is False
        assert suggestion["next_window"] == "afternoon"
        assert suggestion["minutes_until"] == 60

    def test_pre_market_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is False
        assert suggestion["next_window"] == "opening"
        assert suggestion["minutes_until"] == 90

    def test_night_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 3, 0, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is False
        assert suggestion["next_window"] == "opening"
        assert suggestion["minutes_until"] == 390  # 6h 30m

    def test_post_market_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 20, 0, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is False
        assert suggestion["next_window"] == "opening"
        assert suggestion["minutes_until"] == 810  # until next day 09:30

    def test_closing_suggestion(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 16, 0, tzinfo=timezone.utc)
        suggestion = tm.suggest_optimal_trading_time(dt)
        assert suggestion["can_trade_now"] is True
        assert suggestion["current_window"] == "closing"


class TestEODClosure:
    def test_should_close_positions_before_1730(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 17, 0, tzinfo=timezone.utc)
        assert tm.should_close_positions(dt) is False

    def test_should_close_positions_at_1730(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 17, 30, tzinfo=timezone.utc)
        assert tm.should_close_positions(dt) is True

    def test_should_close_positions_after_1730(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 17, 45, tzinfo=timezone.utc)
        assert tm.should_close_positions(dt) is True

    def test_time_until_close_morning(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc)
        minutes = tm.get_time_until_close(dt)
        assert minutes == 480  # 8 hours

    def test_time_until_close_after_close(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 19, 0, tzinfo=timezone.utc)
        minutes = tm.get_time_until_close(dt)
        assert minutes == 0


class TestSummary:
    def test_summary_morning(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        summary = tm.get_summary(dt)
        assert summary["current_window"] == "morning"
        assert summary["can_trade"] is True
        assert summary["risk_multiplier"] == 1.0
        assert summary["max_positions"] == 5
        assert summary["minutes_until_close"] == 450
        assert summary["should_close_positions"] is False
        assert summary["optimal_trading_suggestion"]["can_trade_now"] is True

    def test_summary_lunch(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
        summary = tm.get_summary(dt)
        assert summary["current_window"] == "lunch"
        assert summary["can_trade"] is False
        assert summary["risk_multiplier"] == 0.5
        assert summary["max_positions"] == 2
        assert summary["optimal_trading_suggestion"]["can_trade_now"] is False

    def test_summary_night(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 3, 0, tzinfo=timezone.utc)
        summary = tm.get_summary(dt)
        assert summary["current_window"] == "night"
        assert summary["can_trade"] is False
        assert summary["risk_multiplier"] == 0.0
        assert summary["max_positions"] == 0


class TestCustomWindows:
    def test_custom_window_override(self):
        custom = [
            WindowConfig(
                window=TradingWindow.MORNING,
                start=time(10, 0),
                end=time(11, 30),
                can_trade=True,
                risk_multiplier=2.0,
                max_positions=10,
            ),
        ]
        tm = TimeBasedTradingManager(windows=custom)
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.get_risk_multiplier(dt) == 2.0
        assert tm.get_max_positions(dt) == 10

    def test_empty_windows_uses_defaults(self):
        tm = TimeBasedTradingManager(windows=None)
        dt = datetime(2026, 5, 22, 10, 30, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.MORNING
        assert tm.can_trade_now(dt) is True


class TestEdgeCases:
    def test_exact_window_end_boundary(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 18, 0, 0, tzinfo=timezone.utc)
        # 18:00:00 is the boundary between CLOSING and POST_MARKET
        # Half-open interval means CLOSING ends at 18:00 (exclusive), POST_MARKET starts at 18:00 (inclusive)
        assert tm.get_current_window(dt) == TradingWindow.POST_MARKET

    def test_midnight_boundary(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 0, 0, 0, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.NIGHT

    def test_just_before_closing(self):
        tm = TimeBasedTradingManager()
        dt = datetime(2026, 5, 22, 17, 59, 59, tzinfo=timezone.utc)
        assert tm.get_current_window(dt) == TradingWindow.CLOSING

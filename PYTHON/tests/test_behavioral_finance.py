"""
test_behavioral_finance.py — Behavioral Finance Guard Tests
"""

import pytest
from datetime import datetime, timezone
from risk.behavioral_finance import BehavioralFinanceGuard, TradeResult


class TestBehavioralFinanceGuard:
    def test_consecutive_losses_cooldown(self):
        guard = BehavioralFinanceGuard(consecutive_losses_limit=3)
        for i in range(3):
            guard.update_trade(TradeResult(pnl=-10, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        allowed, reason, meta = guard.can_trade({})
        assert allowed is False
        assert "Cooldown" in reason

    def test_consecutive_losses_resets_on_win(self):
        guard = BehavioralFinanceGuard(consecutive_losses_limit=3)
        guard.update_trade(TradeResult(pnl=-10, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        guard.update_trade(TradeResult(pnl=5, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        guard.update_trade(TradeResult(pnl=-10, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        allowed, reason, meta = guard.can_trade({})
        assert allowed is True

    def test_fomo_detected(self):
        guard = BehavioralFinanceGuard()
        prices = [100.0, 100.5, 101.0, 102.1]
        volumes = [1000, 1000, 1000, 4000]
        result = guard.check_fomo(prices, volumes)
        assert result["fomo"] is True
        assert result["reduction"] == 0.5

    def test_fomo_not_detected(self):
        guard = BehavioralFinanceGuard()
        prices = [100.0, 100.1, 100.2, 100.3]
        volumes = [1000, 1000, 1000, 1000]
        result = guard.check_fomo(prices, volumes)
        assert result["fomo"] is False
        assert result["reduction"] == 1.0

    def test_loss_aversion_alert(self):
        guard = BehavioralFinanceGuard(loss_aversion_ratio_threshold=0.5)
        # Wins fast (10s), losses slow (100s)
        for _ in range(5):
            guard.update_trade(TradeResult(pnl=10, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        for _ in range(5):
            guard.update_trade(TradeResult(pnl=-5, duration_seconds=100, timestamp=datetime.now(timezone.utc)))
        result = guard.check_loss_aversion()
        assert result["alert"] is True
        assert result["ratio"] < 0.5

    def test_loss_aversion_no_alert(self):
        guard = BehavioralFinanceGuard(loss_aversion_ratio_threshold=0.5)
        for _ in range(5):
            guard.update_trade(TradeResult(pnl=10, duration_seconds=100, timestamp=datetime.now(timezone.utc)))
        for _ in range(5):
            guard.update_trade(TradeResult(pnl=-5, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        result = guard.check_loss_aversion()
        assert result["alert"] is False
        assert result["ratio"] > 0.5

    def test_daily_trade_limit(self):
        guard = BehavioralFinanceGuard(max_daily_trades=2)
        guard.update_trade(TradeResult(pnl=10, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        guard.update_trade(TradeResult(pnl=10, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        allowed, reason, meta = guard.can_trade({})
        assert allowed is False
        assert "Daily trade limit" in reason

    def test_drawdown_scale_normal(self):
        guard = BehavioralFinanceGuard()
        result = guard.calculate_drawdown_scale(100_000, 98_000)
        assert result["scale"] == 1.0
        assert result["drawdown"] == 0.02

    def test_drawdown_scale_medium(self):
        guard = BehavioralFinanceGuard()
        result = guard.calculate_drawdown_scale(100_000, 94_000)
        assert result["scale"] == 0.5
        assert result["drawdown"] == 0.06

    def test_drawdown_scale_high(self):
        guard = BehavioralFinanceGuard()
        result = guard.calculate_drawdown_scale(100_000, 85_000)
        assert result["scale"] == 0.25
        assert result["drawdown"] == 0.15

    def test_overconfidence_detected(self):
        guard = BehavioralFinanceGuard(overconfidence_window=10, overconfidence_win_streak=8)
        for i in range(10):
            pnl = 10 if i < 9 else -1  # 9 wins out of 10
            guard.update_trade(TradeResult(pnl=pnl, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        result = guard.check_overconfidence()
        assert result["alert"] is True
        assert result["reduction"] == 0.75

    def test_overconfidence_not_detected(self):
        guard = BehavioralFinanceGuard(overconfidence_window=10, overconfidence_win_streak=8)
        for i in range(10):
            pnl = 10 if i < 5 else -5
            guard.update_trade(TradeResult(pnl=pnl, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        result = guard.check_overconfidence()
        assert result["alert"] is False
        assert result["reduction"] == 1.0

    def test_behavioral_score_high(self):
        guard = BehavioralFinanceGuard()
        for _ in range(3):
            guard.update_trade(TradeResult(pnl=10, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        score = guard.get_behavioral_score()
        assert score >= 80.0

    def test_behavioral_score_low(self):
        guard = BehavioralFinanceGuard()
        for _ in range(5):
            guard.update_trade(TradeResult(pnl=-10, duration_seconds=60, timestamp=datetime.now(timezone.utc)))
        score = guard.get_behavioral_score()
        assert score < 50.0

    def test_reset_daily(self):
        guard = BehavioralFinanceGuard(max_daily_trades=1)
        guard.update_trade(TradeResult(pnl=10, duration_seconds=10, timestamp=datetime.now(timezone.utc)))
        assert guard.can_trade({})[0] is False
        guard.reset_daily()
        assert guard.can_trade({})[0] is True

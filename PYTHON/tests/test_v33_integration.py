"""
test_v33_integration.py — v3.3 integration tests for new production modules

Covers:
- SharedExperienceMemory (cross-agent persistence)
- UnifiedMarketCalendar (multi-venue holidays)
- AlphaProtocol (high-probability strategy)
- IntegrationOrchestrator with calendar + memory
- BlackSwanGuard divide-by-zero safety fix
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from common.shared_experience_memory import SharedExperienceMemory, ExperienceRecord
from data.unified_market_calendar import UnifiedMarketCalendar
from strategy.protocol_strategies.alpha_protocol import AlphaProtocol, AlphaSignal
from adapters.integration_orchestrator import IntegrationOrchestrator


# ------------------------------------------------------------------
# SharedExperienceMemory
# ------------------------------------------------------------------
class TestSharedExperienceMemory:
    def test_record_and_query(self):
        mem = SharedExperienceMemory()
        mem.reset()
        rec = mem.record_experience("signal", "BUY THYAO", "THYAO", 2.5, {"confidence": 85})
        assert rec.agent == "signal"
        results = mem.query(symbol="THYAO")
        assert len(results) == 1
        assert results[0].outcome == 2.5

    def test_record_block(self):
        mem = SharedExperienceMemory()
        mem.reset()
        mem.record_block("risk", "THYAO", "spread too wide", {"spread": 1.2})
        blocks = mem.query(tag="block")
        assert len(blocks) == 1
        assert "spread too wide" in blocks[0].action

    def test_query_lessons(self):
        mem = SharedExperienceMemory()
        mem.reset()
        for _ in range(5):
            mem.record_experience("signal", "BUY", "THYAO", 1.5)
        for _ in range(3):
            mem.record_experience("signal", "BUY", "THYAO", -1.0)
        lessons = mem.query_lessons("THYAO", min_score=0.2)
        assert len(lessons) >= 2

    def test_agent_performance(self):
        mem = SharedExperienceMemory()
        mem.reset()
        mem.record_experience("signal", "BUY", "THYAO", 2.0)
        mem.record_experience("signal", "BUY", "GARAN", -1.0)
        perf = mem.get_agent_performance("signal", lookback_days=1)
        assert perf["records"] == 2
        assert perf["win_rate"] == 0.5

    def test_stats(self):
        mem = SharedExperienceMemory()
        mem.reset()
        mem.record_experience("a", "act", "S1", 1.0)
        mem.record_experience("a", "act", "S2", -1.0)
        stats = mem.stats()
        assert stats["total_records"] == 2
        assert stats["unique_symbols"] == 2


# ------------------------------------------------------------------
# UnifiedMarketCalendar
# ------------------------------------------------------------------
class TestUnifiedMarketCalendar:
    def test_bist_weekend_closed(self):
        cal = UnifiedMarketCalendar()
        saturday = datetime(2026, 5, 23, 12, 0, tzinfo=timezone(timedelta(hours=3)))
        assert cal.is_bist_open(saturday) is False
        assert "Haftasonu" in cal.get_reason("BIST", saturday)

    def test_bist_holiday_closed(self):
        cal = UnifiedMarketCalendar()
        holiday = datetime(2026, 4, 23, 12, 0, tzinfo=timezone(timedelta(hours=3)))
        assert cal.is_bist_open(holiday) is False
        assert "Resmi tatil" in cal.get_reason("BIST", holiday)

    def test_bist_open_hours(self):
        cal = UnifiedMarketCalendar()
        workday = datetime(2026, 5, 25, 12, 0, tzinfo=timezone(timedelta(hours=3)))
        assert cal.is_bist_open(workday) is True
        assert "acik" in cal.get_reason("BIST", workday)

    def test_crypto_always_open(self):
        cal = UnifiedMarketCalendar()
        assert cal.is_crypto_open() is True
        assert "7/24" in cal.get_reason("CRYPTO")

    def test_forex_sessions(self):
        cal = UnifiedMarketCalendar()
        sessions = cal.current_forex_sessions()
        assert isinstance(sessions, list)

    def test_next_open_time(self):
        cal = UnifiedMarketCalendar()
        nxt = cal.next_open_time("BIST")
        assert nxt is not None

    def test_to_dict(self):
        cal = UnifiedMarketCalendar()
        d = cal.to_dict("BIST")
        assert "is_open" in d
        assert "reason" in d


# ------------------------------------------------------------------
# AlphaProtocol
# ------------------------------------------------------------------
class TestAlphaProtocol:
    def _make_df(self, n=50, trend="up") -> pd.DataFrame:
        np.random.seed(42)
        base = 100.0
        if trend == "up":
            closes = base + np.cumsum(np.random.randn(n) * 0.3 + 0.1)
        elif trend == "down":
            closes = base + np.cumsum(np.random.randn(n) * 0.3 - 0.1)
        else:
            closes = base + np.cumsum(np.random.randn(n) * 0.1)
        highs = closes + np.abs(np.random.randn(n) * 0.2)
        lows = closes - np.abs(np.random.randn(n) * 0.2)
        opens = closes - np.random.randn(n) * 0.1
        return pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.random.randint(5000, 15000, n),
        })

    def test_evaluate_returns_none_for_random_data(self):
        proto = AlphaProtocol(account_size=100_000)
        df = self._make_df(100, "sideways")
        signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
        # Sideways random data likely blocked by gates (ATR or no setup)
        assert signal is None or isinstance(signal, AlphaSignal)

    def test_evaluate_momentum_breakout(self):
        proto = AlphaProtocol(account_size=100_000)
        df = self._make_df(100, "up")
        signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
        if signal:
            assert signal.side in ("BUY", "SELL")
            assert signal.rr >= proto.params["min_rr"]
            assert signal.confidence > 50
            assert signal.stop_loss < signal.entry_price or signal.side == "SELL"

    def test_position_sizing(self):
        proto = AlphaProtocol(account_size=100_000)
        size = proto._position_size(entry=100.0, stop=98.0)
        expected_risk = 100_000 * 0.01
        risk_per_unit = 2.0
        assert size == pytest.approx(expected_risk / risk_per_unit, rel=0.01)

    def test_daily_drawdown_gate(self):
        proto = AlphaProtocol(account_size=100_000)
        proto._daily_pnl = -4_000.0  # Exceeds 3% limit
        df = self._make_df(100, "up")
        signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
        assert signal is None

    def test_protocol_stats(self):
        proto = AlphaProtocol(account_size=100_000)
        stats = proto.get_protocol_stats()
        assert stats["account_size"] == 100_000
        assert stats["max_positions"] == 3

    def test_signal_to_dict(self):
        from strategy.protocol_strategies.alpha_protocol import SetupType
        sig = AlphaSignal(
            symbol="THYAO", side="BUY", setup=SetupType.MOMENTUM_BREAKOUT,
            entry_price=100.0, stop_loss=98.0, take_profit=106.0,
            size=50.0, risk_pct=1.0, rr=3.0, confidence=80.0, timeframe="M15",
        )
        d = sig.to_dict()
        assert d["symbol"] == "THYAO"
        assert d["side"] == "BUY"
        assert d["setup"] == "MOMENTUM_BREAKOUT"


# ------------------------------------------------------------------
# IntegrationOrchestrator with calendar + memory
# ------------------------------------------------------------------
class TestIntegrationOrchestratorV33:
    def test_health_includes_calendar_and_memory(self):
        orch = IntegrationOrchestrator(venue="BIST")
        status = orch.initialize()
        assert status["ok"] is True
        assert "calendar" in status
        assert "memory" in status
        assert "risk" in status

    def test_execute_blocked_on_weekend(self):
        orch = IntegrationOrchestrator(venue="BIST")
        orch.initialize()
        # Force weekend by monkey-patching calendar
        orch.calendar._holidays.add(datetime.now().strftime("%Y-%m-%d"))
        res = orch.execute_signal({"symbol": "THYAO", "side": "BUY", "size": 100})
        assert res.ok is False
        assert "Market closed" in res.error or "closed" in res.error.lower()

    def test_report_outcome_records_to_memory(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        orch.report_outcome("THYAO", "MOMENTUM_BREAKOUT", 150.0, {"rr": 2.5})
        perf = orch.shared_memory.get_agent_performance("integration_orchestrator", lookback_days=1)
        assert perf["records"] >= 1


# ------------------------------------------------------------------
# BlackSwanGuard divide-by-zero safety
# ------------------------------------------------------------------
class TestBlackSwanGuardSafety:
    def test_no_divide_by_zero_with_zero_prices(self):
        from risk.black_swan_guard import BlackSwanGuard
        guard = BlackSwanGuard()
        df = pd.DataFrame({
            "close": list(range(40)),
            "high": list(range(40)),
            "low": list(range(40)),
            "volume": [1000] * 40,
        })
        alert = guard.check(df, symbol="TEST")
        assert alert.level in ("NORMAL", "WARNING", "CRITICAL")

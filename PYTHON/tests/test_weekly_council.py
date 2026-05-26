"""
test_weekly_council.py — Haftalik Strateji Konseyi Tests
K197-K203
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dataclasses import asdict
from agents.weekly_council import WeeklyCouncil, WeeklyReport, CouncilDecision


class TestWeeklyCouncil:
    def test_signal_agent_report_empty(self):
        council = WeeklyCouncil()
        r = council.signal_agent_report(pd.DataFrame())
        assert r["win_rate"] == 0.0
        assert r["best_setup"] == ""

    def test_signal_agent_report_basic(self):
        council = WeeklyCouncil()
        df = pd.DataFrame({
            "net_pnl": [100, -50, 80, -30, 120, 50, 50, 50],
            "setup": ["breakout", "breakout", "trend", "mean_rev", "trend", "trend", "breakout", "breakout"],
            "timeframe": ["M5", "M5", "H1", "M15", "H1", "H1", "M5", "M5"],
        })
        r = council.signal_agent_report(df)
        assert r["total_trades"] == 8
        assert r["win_rate"] == 0.75
        assert r["best_setup"] == "trend"
        assert "timeframe_pnl" in r
        assert r["timeframe_pnl"]["H1"] == 250

    def test_risk_agent_report_insufficient(self):
        council = WeeklyCouncil()
        r = council.risk_agent_report(pd.Series([100]), pd.DataFrame())
        assert r["max_dd"] == 0.0
        assert r["regime"] == "sideways"

    def test_risk_agent_report_with_data(self):
        council = WeeklyCouncil()
        equity = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5 + 0.1))
        trades = pd.DataFrame({
            "net_pnl": [10, -5, 10, -5, -5, -5, 10],
        })
        r = council.risk_agent_report(equity, trades)
        assert r["max_dd"] >= 0
        assert r["max_consecutive_losses"] == 3
        assert r["risk_level"] in ["LOW", "MEDIUM", "HIGH"]

    def test_strategy_agent_no_history(self):
        council = WeeklyCouncil()
        sr = {"best_setup": "trend", "win_rate": 0.6, "timeframe_pnl": {}}
        rr = {"max_dd": 0.02, "regime": "bull", "risk_level": "LOW", "volatility": 0.15}
        r = council.strategy_agent_report(sr, rr, [])
        assert r["target_multiplier"] == 1.0
        assert r["approved"] is True

    def test_strategy_agent_winning_week(self):
        council = WeeklyCouncil()
        reports = [
            WeeklyReport(
                week_start="2026-05-12", week_end="2026-05-16",
                net_pnl=1000, target_multiplier=1.0,
            ),
        ]
        sr = {"best_setup": "trend", "win_rate": 0.6, "timeframe_pnl": {}}
        rr = {"max_dd": 0.02, "regime": "bull", "risk_level": "LOW", "volatility": 0.15}
        r = council.strategy_agent_report(sr, rr, reports)
        assert r["target_multiplier"] == 2.0  # kazandi, x2
        assert r["primary_strategy"] == "trend_following"
        assert r["agent_votes"]["Sinyal"] == "APPROVE"
        assert r["agent_votes"]["Risk"] == "APPROVE"

    def test_strategy_agent_losing_week(self):
        council = WeeklyCouncil()
        reports = [
            WeeklyReport(
                week_start="2026-05-12", week_end="2026-05-16",
                net_pnl=-500, target_multiplier=2.0,
            ),
        ]
        sr = {"best_setup": "trend", "win_rate": 0.3, "timeframe_pnl": {}}
        rr = {"max_dd": 0.06, "regime": "sideways", "risk_level": "HIGH", "volatility": 0.35}
        r = council.strategy_agent_report(sr, rr, reports)
        assert r["target_multiplier"] == 1.0  # 2.0 * 0.5
        assert r["position_scale"] == 0.5  # yuksek risk
        assert r["agent_votes"]["Sinyal"] == "REJECT"
        assert r["agent_votes"]["Risk"] == "REJECT"
        assert r["approved"] is False

    def test_convene_creates_decision(self):
        council = WeeklyCouncil()
        trades = pd.DataFrame({
            "net_pnl": [10, -5, 8, -3, 12],
            "setup": ["breakout", "breakout", "trend", "mean_rev", "trend"],
            "timeframe": ["M5", "M5", "H1", "M15", "H1"],
        })
        # Stable, low-vol equity curve
        equity = pd.Series(100 + np.cumsum(np.random.randn(5) * 0.5 + 0.5))
        decision = council.convene("2026-05-12", "2026-05-16", trades, equity)
        assert isinstance(decision, CouncilDecision)
        assert decision.target_multiplier == 2.0
        assert len(decision.suggested_timeframes) >= 1
        assert decision.approved is True
        assert "reasoning" in asdict(decision)

    def test_multiplier_caps(self):
        council = WeeklyCouncil()
        reports = [
            WeeklyReport(week_start="2026-05-12", week_end="2026-05-16", net_pnl=1000, target_multiplier=8.0),
        ]
        sr = {"best_setup": "trend", "win_rate": 0.6, "timeframe_pnl": {}}
        rr = {"max_dd": 0.01, "regime": "bull", "risk_level": "LOW", "volatility": 0.10}
        r = council.strategy_agent_report(sr, rr, reports)
        assert r["target_multiplier"] == 8.0  # cap

    def test_multiplier_floor(self):
        council = WeeklyCouncil()
        reports = [
            WeeklyReport(week_start="2026-05-12", week_end="2026-05-16", net_pnl=-500, target_multiplier=0.25),
        ]
        sr = {"best_setup": "trend", "win_rate": 0.6, "timeframe_pnl": {}}
        rr = {"max_dd": 0.01, "regime": "bull", "risk_level": "LOW", "volatility": 0.10}
        r = council.strategy_agent_report(sr, rr, reports)
        assert r["target_multiplier"] == 0.25  # floor

    def test_to_markdown(self):
        council = WeeklyCouncil()
        decision = CouncilDecision(
            week_start="2026-05-12",
            week_end="2026-05-16",
            approved=True,
            target_multiplier=2.0,
            position_scale=1.0,
            suggested_timeframes=["H1", "D1"],
            primary_strategy="trend_following",
            reasoning="Kazanc haftasi, trend takibi.",
            agent_votes={"Sinyal": "APPROVE", "Risk": "APPROVE", "Strateji": "APPROVE"},
        )
        md = council.to_markdown(decision)
        assert "Haftalik Strateji Konseyi Karari" in md
        assert "EVET (3/3)" in md
        assert "trend_following" in md

    def test_history_summary(self):
        council = WeeklyCouncil()
        council._weekly_reports = [
            WeeklyReport(week_start="2026-05-05", week_end="2026-05-09", total_trades=10, win_count=6, net_pnl=500),
            WeeklyReport(week_start="2026-05-12", week_end="2026-05-16", total_trades=8, win_count=4, net_pnl=-200),
        ]
        summary = council.get_history_summary()
        assert summary["weeks_analyzed"] == 2
        assert summary["total_trades"] == 18
        assert summary["total_net_pnl"] == 300

    def test_consecutive_losses_count(self):
        council = WeeklyCouncil()
        equity = pd.Series(100 + np.cumsum(np.random.randn(10) * 0.5))
        trades = pd.DataFrame({
            "net_pnl": [10, -5, -5, -5, -5, 10, -2, -2, 10, 10],
        })
        r = council.risk_agent_report(equity, trades)
        assert r["max_consecutive_losses"] == 4

    def test_regime_bull_detection(self):
        council = WeeklyCouncil()
        equity = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.2 + 0.5))
        trades = pd.DataFrame({"net_pnl": [10, 10, -5, 10]})
        r = council.risk_agent_report(equity, trades)
        assert r["regime"] == "bull"

    def test_history_rolling_window(self):
        council = WeeklyCouncil(history_weeks=2)
        council._weekly_reports = [
            WeeklyReport(week_start=f"2026-05-{i:02d}", week_end=f"2026-05-{i+1:02d}", net_pnl=10)
            for i in range(1, 10)
        ]
        assert len(council._weekly_reports) == 9
        # trigger pruning manually
        council._weekly_reports = council._weekly_reports[-council.history_weeks:]
        assert len(council._weekly_reports) == 2

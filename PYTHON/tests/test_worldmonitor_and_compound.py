"""
test_worldmonitor_and_compound.py — Tests for WorldMonitor bridge and Compound Growth Protocol

Covers:
- WorldMonitorBridge: RSS parsing, sentiment scoring, macro snapshot
- CompoundGrowthProtocol: Kelly fraction, position sizing, recovery, time decay
- IntegrationOrchestrator with both modules
"""

import pytest
import numpy as np
import pandas as pd
import time
from datetime import datetime, timezone, timedelta

from adapters.worldmonitor_bridge import WorldMonitorBridge, NewsItem
from strategy.protocol_strategies.compound_growth_protocol import CompoundGrowthProtocol, GrowthSignal


# ------------------------------------------------------------------
# WorldMonitorBridge
# ------------------------------------------------------------------
class TestWorldMonitorBridge:
    def test_init(self):
        wm = WorldMonitorBridge()
        assert wm.cache_ttl == 300.0
        assert wm.max_history == 1000

    def test_sentiment_scoring_positive(self):
        wm = WorldMonitorBridge()
        score = wm._score_sentiment("THYAO rekorda yükseliş")
        assert score > 0.3

    def test_sentiment_scoring_negative(self):
        wm = WorldMonitorBridge()
        score = wm._score_sentiment("THYAO çöküş kriz zarar")
        assert score < -0.3

    def test_sentiment_scoring_neutral(self):
        wm = WorldMonitorBridge()
        score = wm._score_sentiment("THYAO fiyatı sabit kaldı")
        assert -0.1 <= score <= 0.1

    def test_extract_symbols(self):
        wm = WorldMonitorBridge()
        syms = wm._extract_symbols("THYAO ve GARAN yükseldi")
        assert "THYAO" in syms
        assert "GARAN" in syms

    def test_parse_rss(self):
        wm = WorldMonitorBridge()
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel><item>
<title>THYAO yükselişte</title>
<link>http://test/1</link>
<pubDate>Mon, 01 Jan 2026 12:00:00 GMT</pubDate>
</item><item>
<title><![CDATA[GARAN düşüşte]]></title>
<link>http://test/2</link>
<pubDate>Mon, 01 Jan 2026 12:05:00 GMT</pubDate>
</item></channel></rss>"""
        items = wm._parse_rss(xml, "TestFeed", "tr")
        assert len(items) == 2
        assert items[0].source == "TestFeed"
        assert "THYAO" in items[0].symbols
        assert items[1].sentiment < 0

    def test_get_latest_news_filter(self):
        wm = WorldMonitorBridge()
        wm._news_queue.append(NewsItem("s", "THYAO up", "u", time.time(), symbols=["THYAO"], sentiment=0.8))
        wm._news_queue.append(NewsItem("s", "GARAN down", "u", time.time(), symbols=["GARAN"], sentiment=-0.5))
        th = wm.get_latest_news(symbol="THYAO")
        assert len(th) == 1
        assert th[0].symbols == ["THYAO"]

    def test_should_halt_no_data(self):
        wm = WorldMonitorBridge()
        halt, reason = wm.should_halt_trading()
        assert halt is False
        assert reason == "OK"

    def test_market_sentiment_empty(self):
        wm = WorldMonitorBridge()
        s = wm.get_market_sentiment()
        assert s["count"] == 0
        assert s["bias"] == "NEUTRAL"


# ------------------------------------------------------------------
# CompoundGrowthProtocol
# ------------------------------------------------------------------
class TestCompoundGrowthProtocol:
    def _make_df(self, n=50, trend="up"):
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

    def test_kelly_fraction(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        k = proto.compute_kelly_fraction(p_win=0.55, avg_win=2.0, avg_loss=1.0)
        assert 0 < k <= proto.params["kelly_cap"]
        # Quarter Kelly of (0.55*2 - 0.45)/2 = 0.325 → 0.08125
        assert k == pytest.approx(0.08125, abs=0.01)

    def test_kelly_zero_on_invalid(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        assert proto.compute_kelly_fraction(0.0, 2.0, 1.0) == 0.0
        assert proto.compute_kelly_fraction(0.55, 0.0, 1.0) == 0.0
        assert proto.compute_kelly_fraction(0.55, 2.0, 0.0) == 0.0

    def test_required_daily_return(self):
        proto = CompoundGrowthProtocol(initial_capital=1000, params={"target_capital": 10000, "max_days": 10})
        r = proto.compute_required_daily_return()
        # 10000 = 1000*(1+r)^10 → r ~ 25.9%
        assert r > 0.20

    def test_recovery_multiplier(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        assert proto.compute_recovery_multiplier(0.0) == 1.0
        m = proto.compute_recovery_multiplier(-0.02)
        assert m > 1.0
        assert m <= proto.params["recovery_max_mult"]

    def test_time_decay_factor(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        # Cannot reliably test exact time without mocking, but ensure 0-1 range
        td = proto.compute_time_decay_factor("BIST")
        assert 0.0 <= td <= 1.0

    def test_position_sizing(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        size = proto.compute_position_size(entry=100.0, stop=98.0, kelly=0.1, recovery=1.0, time_decay=1.0)
        # Risk = 1000 * 0.1 = 100, but max daily loss = 3% (30). Risk per unit = 2. Size = 15.
        assert size == pytest.approx(15.0, abs=0.1)

    def test_update_capital_compound(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        proto.update_capital(50.0)
        assert proto.current_capital == 1050.0
        assert proto.peak_capital == 1050.0
        proto.update_capital(-20.0)
        assert proto.current_capital == 1030.0
        assert proto.daily_pnl == 30.0

    def test_drawdown_halving(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        proto._drawdown = 0.06
        k = proto.compute_kelly_fraction(p_win=0.55, avg_win=2.0, avg_loss=1.0)
        # Kelly should be halved
        assert k < 0.05

    def test_max_drawdown_halt(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        proto._drawdown = 0.12
        df = self._make_df(100, "up")
        signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
        assert signal is None

    def test_daily_loss_limit(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        proto.daily_pnl = -35.0  # Exceeds 3% of 1000
        df = self._make_df(100, "up")
        signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
        assert signal is None

    def test_projection_returns_list(self):
        proto = CompoundGrowthProtocol(initial_capital=1000, params={"max_days": 5})
        traj = proto.project_growth(trades_per_day=2)
        assert len(traj) == 6  # day 0..5
        assert traj[0]["capital"] == 1000

    def test_protocol_stats(self):
        proto = CompoundGrowthProtocol(initial_capital=1000)
        stats = proto.get_protocol_stats()
        assert stats["initial_capital"] == 1000
        assert stats["current_capital"] == 1000
        assert stats["required_daily_return"] >= 0


# ------------------------------------------------------------------
# Integration
# ------------------------------------------------------------------
class TestIntegrationWorldMonitorCompound:
    def test_worldmonitor_init(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        assert orch.worldmonitor is not None
        assert orch.health_check()["worldmonitor"]["active"] is True

    def test_compound_growth_not_initialized(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        res = orch.run_compound_growth_protocol({}, symbol="THYAO")
        assert res["ok"] is False
        assert "not initialized" in res.get("reason", "").lower() or res.get("reason") == "No signal from Compound Growth Protocol"

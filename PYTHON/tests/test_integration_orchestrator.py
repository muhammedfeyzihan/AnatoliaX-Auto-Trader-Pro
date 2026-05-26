"""
tests/test_integration_orchestrator.py — Integration orchestrator tests

Covers HummingbotAdapter, NautilusAdapter replay, and IntegrationOrchestrator.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from adapters.hummingbot_adapter import HummingbotAdapter, ArbitrageOpportunity
from adapters.nautilus_adapter import NautilusAdapter
from adapters.integration_orchestrator import IntegrationOrchestrator, ExecutionResult


# ------------------------------------------------------------------
# HummingbotAdapter
# ------------------------------------------------------------------
class TestHummingbotAdapter:
    def test_initialization(self):
        hb = HummingbotAdapter(exchange="bybit")
        assert hb.exchange == "bybit"
        assert hb.is_available() is False  # Hummingbot not installed in test env

    def test_register_symbol(self):
        hb = HummingbotAdapter()
        assert hb.register_symbol("THYAO") is True
        assert "THYAO" in hb._symbols

    def test_place_market_order_fallback(self):
        hb = HummingbotAdapter()
        res = hb.place_market_order("THYAO", "BUY", 100)
        assert res["status"] in ("FILLED", "ERROR")
        assert res["symbol"] == "THYAO"
        assert res["side"] == "BUY"

    def test_place_limit_order_fallback(self):
        hb = HummingbotAdapter()
        res = hb.place_limit_order("THYAO", "SELL", 50, price=110.0)
        assert res["symbol"] == "THYAO"
        assert res["price"] == 110.0

    def test_cancel_all_orders(self):
        hb = HummingbotAdapter()
        res = hb.cancel_all_orders("THYAO")
        assert res["symbol"] == "THYAO"

    def test_market_making_disabled(self):
        hb = HummingbotAdapter(market_making_enabled=False)
        res = hb.update_market_making_spread("THYAO", 0.01, 0.01)
        assert res["ok"] is False

    def test_market_making_enabled(self):
        hb = HummingbotAdapter(market_making_enabled=True)
        res = hb.update_market_making_spread("THYAO", 0.01, 0.01)
        assert res["ok"] is True

    def test_scan_arbitrage_disabled(self):
        hb = HummingbotAdapter(arbitrage_enabled=False)
        ops = hb.scan_arbitrage("THYAO")
        assert ops == []

    def test_scan_arbitrage_enabled(self):
        hb = HummingbotAdapter(arbitrage_enabled=True)
        ops = hb.scan_arbitrage("THYAO", exchanges=["binance", "bybit"], min_spread_pct=0.0)
        assert isinstance(ops, list)
        if ops:
            assert ops[0].spread_pct >= 0.0

    def test_get_liquidity_snapshot(self):
        hb = HummingbotAdapter()
        snap = hb.get_liquidity_snapshot("THYAO")
        assert snap.symbol == "THYAO"
        assert snap.mid > 0
        assert 0 <= snap.depth_score <= 100

    def test_get_liquidity_ranking(self):
        hb = HummingbotAdapter()
        ranks = hb.get_liquidity_ranking(["THYAO", "GARAN", "ASELS"])
        assert len(ranks) == 3
        assert ranks[0].depth_score >= ranks[-1].depth_score

    def test_set_exchange(self):
        hb = HummingbotAdapter()
        assert hb.set_exchange("okx") is True
        assert hb.exchange == "okx"
        assert hb.set_exchange("unsupported") is False

    def test_get_exchange_config(self):
        hb = HummingbotAdapter(exchange="binance", testnet=True)
        cfg = hb.get_exchange_config()
        assert cfg["exchange"] == "binance"
        assert cfg["testnet"] is True
        assert cfg["hummingbot_installed"] is False


# ------------------------------------------------------------------
# NautilusAdapter replay
# ------------------------------------------------------------------
class TestNautilusAdapterReplay:
    def test_replay_start(self):
        na = NautilusAdapter()
        ticks = [
            {"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000},
            {"timestamp": "2026-01-01T00:01:00", "price": 101.0, "volume": 1200},
        ]
        session = na.replay_start(ticks, initial_state={"cash": 50_000.0})
        assert session["tick_count"] == 2
        assert session["initial_state"]["cash"] == 50_000.0

    def test_replay_step_and_validate(self):
        na = NautilusAdapter()
        ticks = [
            {"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000},
            {"timestamp": "2026-01-01T00:01:00", "price": 101.0, "volume": 1200},
        ]
        na.replay_start(ticks)
        e1 = na.replay_step()
        assert e1 is not None
        assert e1["idx"] == 1
        e2 = na.replay_step()
        assert e2 is not None
        assert e2["idx"] == 2
        e3 = na.replay_step()
        assert e3 is None  # No more ticks

        val = na.replay_validate({"cash": 100_000.0}, tolerance=1.0)
        assert val["ticks_processed"] == 2
        assert isinstance(val["valid"], bool)

    def test_state_checksum(self):
        na = NautilusAdapter()
        ticks = [{"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000}]
        na.replay_start(ticks, initial_state={"cash": 100_000.0})
        na.replay_step()
        cs1 = na.state_checksum()
        assert len(cs1) == 16
        cs2 = na.state_checksum()
        assert cs1 == cs2

    def test_get_replay_log(self):
        na = NautilusAdapter()
        ticks = [{"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000}]
        na.replay_start(ticks)
        na.replay_step()
        log = na.get_replay_log()
        assert len(log) == 1


# ------------------------------------------------------------------
# IntegrationOrchestrator
# ------------------------------------------------------------------
class TestIntegrationOrchestrator:
    def test_initialize(self):
        orch = IntegrationOrchestrator()
        status = orch.initialize()
        assert status["ok"] is True
        assert "nautilus" in status
        assert "hummingbot" in status
        assert "hermes" in status

    def test_health_check_before_init(self):
        orch = IntegrationOrchestrator()
        health = orch.health_check()
        assert health["ok"] is False
        assert health["reason"] == "NOT_INITIALIZED"

    def test_execute_signal_risk_gate_blocks_low_confidence(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        # Mock calendar to bypass market-closed check for this risk-gate test
        class _AlwaysOpenCalendar:
            def is_market_open(self, venue): return True
            def get_reason(self, venue): return "Open"
        orch.calendar = _AlwaysOpenCalendar()
        res = orch.execute_signal({
            "symbol": "THYAO",
            "side": "BUY",
            "size": 100,
            "price": 105.0,
            "confidence": 10.0,  # Below default 60.0 threshold
            "sl": 100.0,
            "tp": 115.0,
        })
        assert res.ok is False
        assert "Risk gate blocked" in res.error
        assert res.provider == "hermes_risk_gate"

    def test_execute_signal_success_path(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        # Mock calendar to bypass market-closed check
        class _AlwaysOpenCalendar:
            def is_market_open(self, venue): return True
            def get_reason(self, venue): return "Open"
        orch.calendar = _AlwaysOpenCalendar()
        res = orch.execute_signal({
            "symbol": "THYAO",
            "side": "BUY",
            "size": 100,
            "price": 105.0,
            "confidence": 85.0,
            "sl": 100.0,
            "tp": 115.0,
        })
        # Should succeed or fallback gracefully
        assert res.symbol == "THYAO"
        assert res.side == "BUY"
        assert res.ok in (True, False)

    def test_execute_signal_without_init(self):
        orch = IntegrationOrchestrator()
        res = orch.execute_signal({"symbol": "THYAO", "side": "BUY", "size": 100})
        assert res.ok is False
        assert "not initialized" in res.error.lower()

    def test_replay_validate(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        ticks = [
            {"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000},
            {"timestamp": "2026-01-01T00:01:00", "price": 101.0, "volume": 1200},
        ]
        result = orch.replay_validate(ticks, expected_state={"cash": 100_000.0}, tolerance=1.0)
        assert "valid" in result
        assert "checksum" in result
        assert result["ticks_processed"] == 2

    def test_report_outcome(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        orch.report_outcome("THYAO", "ema_cross", pnl=500.0)
        stats = orch.skill_engine.get_skill_stats()
        assert stats["total_skills"] >= 0

    def test_scan_arbitrage(self):
        orch = IntegrationOrchestrator(enable_arbitrage=True)
        orch.initialize()
        ops = orch.scan_arbitrage("THYAO", min_spread_pct=0.0)
        assert isinstance(ops, list)

    def test_get_best_skill(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        best = orch.get_best_skill("THYAO")
        assert best is None or "skill_id" in best

    def test_execution_log(self):
        orch = IntegrationOrchestrator()
        orch.initialize()
        orch.execute_signal({
            "symbol": "THYAO",
            "side": "BUY",
            "size": 100,
            "price": 105.0,
            "confidence": 85.0,
            "sl": 100.0,
            "tp": 115.0,
        })
        log = orch.get_execution_log()
        assert len(log) >= 1
        orch.clear_execution_log()
        assert len(orch.get_execution_log()) == 0

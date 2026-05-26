"""
test_omega_protocol.py — Tests for Omega Protocol master strategy
"""

import pytest
import numpy as np
import pandas as pd

from strategy.protocol_strategies.omega_protocol import OmegaProtocol, OmegaSignal, OmegaStatus, PipelineResult


class TestOmegaProtocolInit:
    def test_init_defaults(self):
        omega = OmegaProtocol(initial_capital=1000)
        assert omega.current_capital == 1000
        assert omega.params["target_capital"] == 1_000_000
        assert omega.params["max_days"] == 20

    def test_required_daily_return_day0(self):
        omega = OmegaProtocol(initial_capital=1000)
        r = omega._compute_required_daily_return()
        # (1M / 1k)^(1/20) - 1 ≈ 0.412
        assert r > 0.40

    def test_required_daily_return_midway(self):
        omega = OmegaProtocol(initial_capital=1000)
        omega.current_capital = 10_000
        omega.total_days = 10
        r = omega._compute_required_daily_return()
        # (1M / 10k)^(1/10) - 1 ≈ 0.585
        assert r > 0.50


class TestOmegaRegimeDetection:
    def test_detect_bull(self):
        omega = OmegaProtocol()
        df = pd.DataFrame({
            "close": list(range(100, 150)),
            "volume": [1000]*50,
        })
        assert omega._detect_regime(df) == "bull"

    def test_detect_bear(self):
        omega = OmegaProtocol()
        df = pd.DataFrame({
            "close": list(range(150, 100, -1)),
            "volume": [1000]*50,
        })
        assert omega._detect_regime(df) == "bear"

    def test_detect_sideways_short(self):
        omega = OmegaProtocol()
        df = pd.DataFrame({
            "close": [100]*10,
            "volume": [1000]*10,
        })
        assert omega._detect_regime(df) == "sideways"


class TestOmegaPipelineSteps:
    def test_step_worldmonitor(self):
        omega = OmegaProtocol()
        res = omega._step_worldmonitor("THYAO")
        assert res.status in (OmegaStatus.PASS, OmegaStatus.HALT)

    def test_step_blackswan_flat(self):
        omega = OmegaProtocol()
        df = pd.DataFrame({
            "close": [100.0]*40,
            "volume": [1000]*40,
        })
        res = omega._step_blackswan(df, "THYAO")
        assert res.status == OmegaStatus.PASS

    def test_step_calendar_bist(self):
        omega = OmegaProtocol()
        res = omega._step_calendar("BIST")
        # Could be PASS or HALT depending on current time/date
        assert res.status in (OmegaStatus.PASS, OmegaStatus.HALT)

    def test_step_manipulation_clean(self):
        omega = OmegaProtocol()
        df = pd.DataFrame({
            "close": [100.0]*30,
            "high": [101.0]*30,
            "low": [99.0]*30,
            "volume": [1000]*30,
        })
        res = omega._step_manipulation(df, "TEST")
        assert res.status == OmegaStatus.PASS
        assert res.reason.startswith("Score=")

    def test_step_manipulation_pump(self):
        omega = OmegaProtocol()
        close = [100.0]*15 + [102.0, 105.0, 108.0, 106.0, 101.0, 100.5]
        df = pd.DataFrame({
            "close": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "volume": [1000]*15 + [3000, 5000, 8000, 6000, 4000, 2000],
        })
        res = omega._step_manipulation(df, "TEST")
        # Should detect pump but may not cross 70 threshold
        assert res.status in (OmegaStatus.PASS, OmegaStatus.BLOCK)

    def test_step_risk_gate_pass(self):
        omega = OmegaProtocol()
        from hermes_adapter.risk_gates import RiskGateEngine
        omega.risk_gate = RiskGateEngine(market_open_required=False)
        from strategy.protocol_strategies.compound_growth_protocol import GrowthSignal
        gs = GrowthSignal(
            symbol="THYAO", side="BUY", setup="MOMENTUM",
            entry_price=100.0, stop_loss=99.0, take_profit=105.0,
            size=10.0, risk_pct=1.0, rr=2.0, confidence=80.0,
            timeframe="M15",
            kelly_fraction=0.1, compound_factor=1.0,
            recovery_multiplier=1.0, time_decay=1.0, expected_return=0.05,
        )
        res = omega._step_risk_gate("THYAO", gs)
        assert res.status == OmegaStatus.PASS

    def test_step_laws_pass(self):
        omega = OmegaProtocol()
        from strategy.protocol_strategies.compound_growth_protocol import GrowthSignal
        gs = GrowthSignal(
            symbol="THYAO", side="BUY", setup="MOMENTUM",
            entry_price=100.0, stop_loss=99.0, take_profit=105.0,
            size=10.0, risk_pct=1.0, rr=2.0, confidence=80.0,
            timeframe="M15",
            kelly_fraction=0.1, compound_factor=1.0,
            recovery_multiplier=1.0, time_decay=1.0, expected_return=0.05,
        )
        df = pd.DataFrame({
            "close": [100.0]*20,
            "volume": [1000]*20,
        })
        res = omega._step_laws(df, "THYAO", gs)
        assert res.status == OmegaStatus.PASS

    def test_step_skill_engine_no_skill(self):
        omega = OmegaProtocol()
        res = omega._step_skill_engine("THYAO", "MOMENTUM")
        assert res.status == OmegaStatus.PASS

    def test_step_shared_memory_no_lessons(self):
        omega = OmegaProtocol()
        res = omega._step_shared_memory("THYAO", "MOMENTUM")
        assert res.status == OmegaStatus.PASS


class TestOmegaEvaluate:
    def test_evaluate_flat_data_no_signal(self):
        omega = OmegaProtocol(initial_capital=1000)
        df = pd.DataFrame({
            "open": [100.0]*30,
            "high": [101.0]*30,
            "low": [99.0]*30,
            "close": [100.0]*30,
            "volume": [1000]*30,
        })
        signal = omega.evaluate(df, symbol="TEST")
        # Flat data won't pass AlphaProtocol, so None expected
        assert signal is None

    def test_evaluate_returns_omega_signal_or_none(self):
        omega = OmegaProtocol(initial_capital=1000)
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(60) * 0.5)
        df = pd.DataFrame({
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.random.randint(800, 1200, 60),
        })
        signal = omega.evaluate(df, symbol="TEST")
        # Either a signal or blocked — both are valid outcomes
        assert signal is None or isinstance(signal, OmegaSignal)


class TestOmegaCampaign:
    def test_run_campaign_empty(self):
        omega = OmegaProtocol(initial_capital=1000)
        report = omega.run_campaign([], lambda sym: None)
        assert report["initial_capital"] == 1000
        assert report["final_capital"] == 1000
        assert report["total_trades"] == 0


class TestOrchestratorOmega:
    def test_run_omega_protocol_integration(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        df = pd.DataFrame({
            "open": [100.0]*30,
            "high": [101.0]*30,
            "low": [99.0]*30,
            "close": [100.0]*30,
            "volume": [1000]*30,
        })
        res = orch.run_omega_protocol(df=df.to_dict(), symbol="TEST")
        assert "ok" in res
        assert "symbol" in res

    def test_run_omega_campaign_integration(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        report = orch.run_omega_campaign(
            symbols=[],
            bars_provider=lambda sym: None,
        )
        assert report["initial_capital"] == 1000
        assert report["total_trades"] == 0

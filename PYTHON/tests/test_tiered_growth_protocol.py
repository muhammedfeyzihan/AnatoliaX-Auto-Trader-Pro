"""
test_tiered_growth_protocol.py — Tests for Tiered Growth Protocol
"""

import pytest
import numpy as np
import pandas as pd

from strategy.protocol_strategies.tiered_growth_protocol import (
    TieredGrowthProtocol,
    DailyReturnTarget,
    TieredRiskConfig,
    MonthlyProjection,
    TIER_CONFIGS,
)


class TestTieredConfigs:
    def test_all_tiers_have_config(self):
        for tier in DailyReturnTarget:
            assert tier in TIER_CONFIGS
            cfg = TIER_CONFIGS[tier]
            assert cfg.daily_return_pct > 0
            assert cfg.kelly_cap > 0
            assert cfg.min_rr >= 1.0

    def test_pct_1_conservative(self):
        cfg = TIER_CONFIGS[DailyReturnTarget.PCT_1]
        assert cfg.daily_return_pct == 0.01
        assert cfg.kelly_cap == 0.05
        assert cfg.max_drawdown_pct == 3.0
        assert cfg.leverage == 1.0

    def test_pct_100_theoretical(self):
        cfg = TIER_CONFIGS[DailyReturnTarget.PCT_100]
        assert cfg.daily_return_pct == 1.00
        assert cfg.max_drawdown_pct == 80.0
        assert "MATEMATİKSEL" in cfg.description

    def test_config_to_dict(self):
        cfg = TIER_CONFIGS[DailyReturnTarget.PCT_5]
        d = cfg.to_dict()
        assert d["daily_return_pct"] == 5.0
        assert d["kelly_cap"] == 0.15
        assert "timeframes" in d


class TestMathHelpers:
    def test_compound_return_month(self):
        r = TieredGrowthProtocol.compound_return(0.05, 22)
        # (1.05)^22 - 1 ≈ 1.92
        assert r > 1.8

    def test_compound_return_year(self):
        r = TieredGrowthProtocol.compound_return(0.01, 252)
        # (1.01)^252 - 1 ≈ 11.2
        assert r > 10.0

    def test_required_win_rate_simple(self):
        p = TieredGrowthProtocol.required_win_rate(rr=2.0, kelly=0.10)
        # f = (p*2 - (1-p))/2  ->  0.1*2 = 2p - 1 + p  ->  0.2 = 3p - 1  ->  p = 1.2/3 = 0.4
        assert 0.35 < p < 0.45

    def test_risk_of_ruin_zero_edge(self):
        r = TieredGrowthProtocol.risk_of_ruin(0.50, 1.0, 1.0, 0.1, 10)
        assert r >= 0.0

    def test_risk_of_ruin_high_edge(self):
        r = TieredGrowthProtocol.risk_of_ruin(0.70, 2.0, 1.0, 0.1, 10)
        assert r < 0.5


class TestMonthlyProjection:
    def test_pct_5_projection(self):
        proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_5)
        proj = proto.get_monthly_projection(trading_days=22)
        assert proj.target == DailyReturnTarget.PCT_5
        assert proj.total_return_pct > 100  # ~190%
        assert proj.final_capital > 20_000
        assert proj.win_rate_needed > 0
        assert proj.risk_of_ruin >= 0.0

    def test_pct_1_projection_conservative(self):
        proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_1)
        proj = proto.get_monthly_projection(trading_days=22)
        assert proj.total_return_pct < 30  # ~24%
        assert proj.max_expected_dd_pct == 3.0

    def test_all_tier_projections(self):
        proto = TieredGrowthProtocol(initial_capital=10_000)
        projs = proto.get_all_tier_projections(capital=10_000)
        assert len(projs) == len(DailyReturnTarget)
        for name, proj in projs.items():
            assert proj.initial_capital == 10_000
            assert proj.total_return_pct >= 0


class TestTieredProtocolInit:
    def test_init_defaults(self):
        proto = TieredGrowthProtocol()
        assert proto.initial_capital == 10_000
        assert proto.target == DailyReturnTarget.PCT_5

    def test_init_pct_10(self):
        proto = TieredGrowthProtocol(initial_capital=5_000, target=DailyReturnTarget.PCT_10)
        assert proto.current_capital == 5_000
        assert proto.config.daily_return_pct == 0.10


class TestTieredProtocolEvaluate:
    def test_evaluate_flat_no_signal(self):
        proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_1)
        df = pd.DataFrame({
            "open": [100.0]*30,
            "high": [101.0]*30,
            "low": [99.0]*30,
            "close": [100.0]*30,
            "volume": [1000]*30,
        })
        res = proto.evaluate(df, symbol="TEST", venue="FOREX")
        # Flat data won't produce Alpha signal; expected None
        assert res is None

    def test_evaluate_returns_dict_or_none(self):
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(60) * 0.5)
        df = pd.DataFrame({
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.random.randint(800, 1200, 60),
        })
        proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_1)
        res = proto.evaluate(df, symbol="TEST")
        assert res is None or isinstance(res, dict)


class TestTierComparisonTable:
    def test_table_shape(self):
        proto = TieredGrowthProtocol(initial_capital=10_000)
        df = proto.get_tier_comparison_table(capital=10_000)
        assert len(df) == len(DailyReturnTarget)
        assert "Daily %" in df.columns
        assert "Monthly %" in df.columns
        assert "Risk of Ruin" in df.columns


class TestOrchestratorTiered:
    def test_run_tiered_protocol_integration(self):
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
        res = orch.run_tiered_protocol(df=df.to_dict(), symbol="TEST", tier="PCT_1")
        assert "ok" in res
        assert "tier" in res
        assert res["tier"] == "PCT_1"

    def test_run_tiered_scan_empty(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        results = orch.run_tiered_scan(symbols=[], tier="PCT_1")
        assert results == []


class TestStats:
    def test_get_stats(self):
        proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_3)
        stats = proto.get_stats()
        assert stats["current_capital"] == 10_000
        assert stats["target_tier"] == "PCT_3"
        assert "monthly_projection" in stats

"""
tests/test_v33_modules.py — v3.3 missing module tests

Covers:
- MultiMarketPool
- ImmutableExecutionLawEngine
- BlackSwanGuard
- CrashRecoveryManager self-healing
- HummingbotAdapter spread widening
- StrategyRegistry hot-reload
- BayesianOptimizer
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import time
from pathlib import Path

from common.multi_market_pool import MultiMarketPool, MarketSnapshot
from risk.execution_laws import ImmutableExecutionLawEngine, LawVerdict
from risk.black_swan_guard import BlackSwanGuard, BlackSwanAlert
from execution.crash_recovery import CrashRecoveryManager
from adapters.hummingbot_adapter import HummingbotAdapter
from strategy.strategy_registry import StrategyRegistry
from optimization.bayesian_optimizer import BayesianOptimizer


# ------------------------------------------------------------------
# MultiMarketPool
# ------------------------------------------------------------------
class TestMultiMarketPool:
    def test_subscribe_and_list(self):
        pool = MultiMarketPool(max_markets=5)
        added = pool.subscribe(["THYAO", "GARAN", "BTCUSDT"])
        assert sorted(added) == ["BTCUSDT", "GARAN", "THYAO"]
        assert pool.list_symbols() == ["BTCUSDT", "GARAN", "THYAO"]

    def test_max_markets_limit(self):
        pool = MultiMarketPool(max_markets=2)
        added = pool.subscribe(["A", "B", "C"])
        assert len(added) == 2

    def test_update_and_snapshot(self):
        pool = MultiMarketPool()
        pool.subscribe(["THYAO"])
        pool.update("THYAO", price=103.0, bid=102.9, ask=103.1, volume=5000, atr_pct=0.8)
        snap = pool.get_snapshot("THYAO")
        assert snap is not None
        assert snap.price == 103.0
        assert snap.spread_pct > 0

    def test_stale_detection(self):
        pool = MultiMarketPool(stale_seconds=0.01)
        pool.subscribe(["THYAO"])
        pool.update("THYAO", price=100.0)
        time.sleep(0.02)
        snap = pool.get_snapshot("THYAO")
        assert snap.stale is True

    def test_volatility_ranking(self):
        pool = MultiMarketPool()
        pool.subscribe(["A", "B"])
        pool.update("A", price=100.0, atr_pct=2.0)
        pool.update("B", price=100.0, atr_pct=1.0)
        ranks = pool.get_volatility_ranking()
        assert ranks[0][0] == "A"

    def test_to_dataframe(self):
        pool = MultiMarketPool()
        pool.subscribe(["THYAO"])
        pool.update("THYAO", price=100.0)
        df = pool.to_dataframe()
        assert len(df) == 1
        assert "price" in df.columns

    def test_unsubscribe(self):
        pool = MultiMarketPool()
        pool.subscribe(["THYAO"])
        pool.unsubscribe(["THYAO"])
        assert pool.get_snapshot("THYAO") is None


# ------------------------------------------------------------------
# ImmutableExecutionLawEngine
# ------------------------------------------------------------------
class TestImmutableExecutionLawEngine:
    def test_all_pass(self):
        law = ImmutableExecutionLawEngine(strict_mode=True)
        v = law.check(
            signal={"symbol": "THYAO", "side": "BUY", "size": 100, "price": 105.0,
                    "confidence": 80.0, "atr_pct": 2.0, "spread_pct": 0.3,
                    "leverage": 1.0, "prob_win": 0.6, "fake_breakout_prob": 0.1,
                    "liquidation_risk": 0.05, "stale_order_seconds": 0.0},
            state={"equity": 100_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0},
        )
        assert v.allowed is True
        assert v.status.value == "PASS"

    def test_low_confidence_blocked(self):
        law = ImmutableExecutionLawEngine(strict_mode=True)
        v = law.check(
            signal={"confidence": 30.0, "atr_pct": 2.0, "spread_pct": 0.3,
                    "leverage": 1.0, "prob_win": 0.6, "fake_breakout_prob": 0.1,
                    "liquidation_risk": 0.05, "stale_order_seconds": 0.0},
            state={"equity": 100_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0},
        )
        assert v.allowed is False
        assert any("L9_RISK_VERIFY" in r for r in v.reasons)

    def test_black_swan_drawdown_blocked(self):
        law = ImmutableExecutionLawEngine(strict_mode=True)
        v = law.check(
            signal={"confidence": 80.0, "atr_pct": 2.0, "spread_pct": 0.3,
                    "leverage": 1.0, "prob_win": 0.6, "fake_breakout_prob": 0.1,
                    "liquidation_risk": 0.05, "stale_order_seconds": 0.0},
            state={"equity": 85_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0},
        )
        # Peak starts at equity, so drawdown is 0 unless peak > equity
        # Manually set peak higher by first allowing execution
        law._peak_equity = 100_000.0
        v2 = law.check(
            signal={"confidence": 80.0, "atr_pct": 2.0, "spread_pct": 0.3,
                    "leverage": 1.0, "prob_win": 0.6, "fake_breakout_prob": 0.1,
                    "liquidation_risk": 0.05, "stale_order_seconds": 0.0},
            state={"equity": 85_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0},
        )
        assert v2.allowed is False
        assert any("L12_BLACK_SWAN" in r for r in v2.reasons)

    def test_not_initialized_blocked(self):
        law = ImmutableExecutionLawEngine(strict_mode=True)
        v = law.check(
            signal={"confidence": 80.0},
            state={"equity": -1000.0},
        )
        assert v.allowed is False

    def test_global_execution_gate(self):
        law = ImmutableExecutionLawEngine()
        law.update_state({"equity": 100_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0, "uncertainty_score": 0.05})
        assert law.is_execution_allowed() is True
        law.update_state({"equity": 100_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0, "uncertainty_score": 0.25})
        assert law.is_execution_allowed() is False

    def test_block_history(self):
        law = ImmutableExecutionLawEngine(strict_mode=True)
        law.check(signal={"confidence": 10.0}, state={"equity": 100_000.0})
        hist = law.get_block_history()
        assert len(hist) >= 1


# ------------------------------------------------------------------
# BlackSwanGuard
# ------------------------------------------------------------------
class TestBlackSwanGuard:
    def test_normal_data_no_alert(self):
        guard = BlackSwanGuard()
        df = pd.DataFrame({
            "close": [100.0 + i * 0.1 for i in range(40)],
            "high": [100.5 + i * 0.1 for i in range(40)],
            "low": [99.5 + i * 0.1 for i in range(40)],
            "volume": [1000] * 40,
        })
        alert = guard.check(df, symbol="THYAO")
        assert alert.is_black_swan is False
        assert alert.level == "NORMAL"

    def test_flash_crash_detected(self):
        guard = BlackSwanGuard(flash_crash_pct=5.0)
        closes = [100.0 + i * 0.1 for i in range(39)] + [85.0]
        df = pd.DataFrame({
            "close": closes,
            "high": [c + 0.5 for c in closes],
            "low": [c - 0.5 for c in closes],
            "volume": [1000] * 40,
        })
        alert = guard.check(df, symbol="THYAO")
        assert alert.is_black_swan is True
        assert alert.level == "CRITICAL"
        assert "Flash crash" in alert.reason

    def test_halt_and_resume(self):
        guard = BlackSwanGuard()
        guard.halt("TEST")
        assert guard.is_halted() is True
        time.sleep(0.01)
        guard._halt_until = time.time() - 0.01
        assert guard.is_halted() is False

    def test_alert_history(self):
        guard = BlackSwanGuard()
        df = pd.DataFrame({
            "close": list(range(40)),
            "high": list(range(40)),
            "low": list(range(40)),
            "volume": [1000] * 40,
        })
        guard.check(df, symbol="X")
        hist = guard.get_alert_history()
        assert isinstance(hist, list)

    def test_insufficient_data(self):
        guard = BlackSwanGuard()
        df = pd.DataFrame({"close": [1, 2], "high": [2, 3], "low": [0, 1], "volume": [1, 1]})
        alert = guard.check(df)
        assert alert.level == "NORMAL"
        assert "Insufficient data" in alert.reason


# ------------------------------------------------------------------
# CrashRecoveryManager self-healing
# ------------------------------------------------------------------
class TestCrashRecoverySelfHeal:
    def test_checkpoint_and_recover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CrashRecoveryManager(checkpoint_dir=tmpdir)
            mgr.set("equity", 100_000.0)
            mgr.checkpoint(tag="test")
            # Do not reset — recover from existing checkpoint
            state = mgr.recover(tag="test")
            assert state.get("equity") == 100_000.0

    def test_self_heal_validates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CrashRecoveryManager(checkpoint_dir=tmpdir)
            mgr.set("equity", 100_000.0)
            mgr.checkpoint()
            result = mgr.self_heal(validators=[mgr.validate_state_integrity])
            assert result["recovered"] is True

    def test_self_heal_rollback_on_bad_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CrashRecoveryManager(checkpoint_dir=tmpdir)
            mgr.set("equity", 100_000.0)
            mgr.checkpoint(tag="good")
            # Simulate corrupted checkpoint manually
            import json
            bad_path = Path(tmpdir) / "checkpoint_bad_20260101_000000.json"
            with open(bad_path, "w") as f:
                json.dump({"equity": -5000.0}, f)
            result = mgr.self_heal(validators=[mgr.validate_state_integrity])
            # Should skip bad and recover from good
            assert result["recovered"] is True
            assert mgr.get("equity") == 100_000.0

    def test_get_recovery_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CrashRecoveryManager(checkpoint_dir=tmpdir)
            mgr.set("key", "val")
            mgr.checkpoint()
            stats = mgr.get_recovery_stats()
            assert stats["checkpoint_count"] >= 1
            assert "state_keys" in stats


# ------------------------------------------------------------------
# HummingbotAdapter spread widening
# ------------------------------------------------------------------
class TestHummingbotSpreadWidening:
    def test_analyze_spread_widening_insufficient(self):
        hb = HummingbotAdapter()
        res = hb.analyze_spread_widening("THYAO", history=[])
        assert res["trend"] == "INSUFFICIENT_DATA"

    def test_analyze_spread_widening_stable(self):
        hb = HummingbotAdapter()
        from adapters.hummingbot_adapter import LiquiditySnapshot
        hist = [LiquiditySnapshot(symbol="THYAO", exchange="binance", bid=99.5, ask=100.5, mid=100.0, spread_pct=0.5, bid_volume=5000, ask_volume=4800, depth_score=50.0) for _ in range(10)]
        res = hb.analyze_spread_widening("THYAO", history=hist)
        assert res["trend"] == "STABLE"
        assert res["anomaly"] is False

    def test_analyze_spread_widening_anomaly(self):
        hb = HummingbotAdapter()
        from adapters.hummingbot_adapter import LiquiditySnapshot
        hist = [LiquiditySnapshot(symbol="THYAO", exchange="binance", bid=99.5, ask=100.5, mid=100.0, spread_pct=0.5, bid_volume=5000, ask_volume=4800, depth_score=50.0) for _ in range(10)]
        # Add anomalous wide spread entries
        hist += [LiquiditySnapshot(symbol="THYAO", exchange="binance", bid=95.0, ask=105.0, mid=100.0, spread_pct=10.0, bid_volume=100, ask_volume=100, depth_score=5.0) for _ in range(5)]
        res = hb.analyze_spread_widening("THYAO", history=hist)
        assert res["anomaly"] is True
        assert res["recommended_action"] == "AVOID"


# ------------------------------------------------------------------
# StrategyRegistry hot-reload
# ------------------------------------------------------------------
class TestStrategyRegistryHotReload:
    def test_scan_plugins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = StrategyRegistry()
            reg.set_plugin_dir(tmpdir)
            # Write a dummy strategy plugin
            plugin = Path(tmpdir) / "dummy_strategy.py"
            plugin.write_text("""
class DummyStrategy:
    NAME = "dummy"
    VERSION = "1.0"
    def run(self, data, params):
        return 42
""")
            metas = reg.scan_plugins()
            assert len(metas) == 1
            assert metas[0].name == "dummy"

    def test_hot_reload_detects_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = StrategyRegistry(enable_hot_reload=True)
            reg.set_plugin_dir(tmpdir)
            plugin = Path(tmpdir) / "reload_test.py"
            plugin.write_text("class ReloadTest:\n    NAME='reload_test'\n    VERSION='1.0'\n    def run(self,d,p):return 1\n")
            reg.scan_plugins()
            meta = reg.get("reload_test")
            assert meta.version == "1.0"
            # Modify file
            time.sleep(0.05)
            plugin.write_text("class ReloadTest:\n    NAME='reload_test'\n    VERSION='2.0'\n    def run(self,d,p):return 2\n")
            reloaded = reg.check_hot_reload()
            assert any(r["name"] == "reload_test" for r in reloaded)
            new_meta = reg.get("reload_test")
            assert new_meta.version == "2.0"

    def test_validation_hook_blocks_bad_strategy(self):
        reg = StrategyRegistry()
        meta = reg.load_from_module("strategy.gold_mining.m1_strategy", "M1Strategy")
        reg.add_validation_hook(lambda m: (False, "test block"))
        ok, reason = reg._validate(meta)
        assert ok is False
        assert "test block" in reason


# ------------------------------------------------------------------
# BayesianOptimizer
# ------------------------------------------------------------------
class TestBayesianOptimizer:
    def test_fallback_optimization(self):
        opt = BayesianOptimizer({"x": (0.0, 10.0)})

        def objective(params):
            x = params["x"]
            return -(x - 3.0) ** 2 + 100.0

        res = opt.optimize(objective, n_calls=20)
        assert res.best_score > 90.0
        assert 2.0 <= res.best_params["x"] <= 4.0
        assert res.backend == "fallback_random_search"
        assert len(res.convergence) == 20

    def test_maximize_false(self):
        opt = BayesianOptimizer({"x": (0.0, 10.0)}, maximize=False)

        def objective(params):
            return (params["x"] - 3.0) ** 2

        res = opt.optimize(objective, n_calls=20)
        assert res.best_score < 5.0

    def test_local_refinement(self):
        opt = BayesianOptimizer({"x": (0.0, 10.0)})

        def objective(params):
            x = params["x"]
            return -(x - 5.5) ** 2 + 100.0

        res = opt.optimize(objective, n_calls=50)
        assert res.best_score > 95.0

    def test_integer_params(self):
        opt = BayesianOptimizer({"n": (1, 10)})
        sample = opt._random_sample()
        assert isinstance(sample["n"], int)
        assert 1 <= sample["n"] <= 10

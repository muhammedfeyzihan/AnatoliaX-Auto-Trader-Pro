"""
test_strategy_registry.py — Tests for StrategyRegistry (K224)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategy.strategy_registry import StrategyRegistry, StrategyMeta


class DummyStrategy:
    NAME = "dummy"
    VERSION = "1.0"
    DESCRIPTION = "Test strategy"
    TIMEFRAMES = ["M5", "M15"]
    DEFAULT_PARAMS = {"threshold": 100}

    def run(self, data, params):
        return {"signal": "BUY"}


class TestStrategyRegistry:
    def test_register_manual(self):
        reg = StrategyRegistry()
        meta = StrategyMeta(name="manual", version="1.0")
        reg.register(meta, instance=DummyStrategy())
        assert "manual" in reg.list_strategies()

    def test_load_from_module(self):
        reg = StrategyRegistry()
        meta = reg.load_from_module("tests.test_strategy_registry", "DummyStrategy")
        assert meta.name == "dummy"
        assert "dummy" in reg.list_strategies()

    def test_run_strategy(self):
        reg = StrategyRegistry()
        reg.register(StrategyMeta(name="d"), instance=DummyStrategy())
        result = reg.run_strategy("d", data=None, params={})
        assert result["signal"] == "BUY"

    def test_unload(self):
        reg = StrategyRegistry()
        reg.register(StrategyMeta(name="x"), instance=DummyStrategy())
        assert reg.unload("x") is True
        assert "x" not in reg.list_strategies()

    def test_get_nonexistent(self):
        reg = StrategyRegistry()
        assert reg.get("nonexistent") is None

    def test_get_all(self):
        reg = StrategyRegistry()
        reg.register(StrategyMeta(name="a"), instance=DummyStrategy())
        reg.register(StrategyMeta(name="b"), instance=DummyStrategy())
        assert len(reg.get_all()) == 2

    def test_reset(self):
        reg = StrategyRegistry()
        reg.register(StrategyMeta(name="a"), instance=DummyStrategy())
        reg.reset()
        assert len(reg.list_strategies()) == 0

    def test_run_missing_method(self):
        class NoRun:
            pass
        reg = StrategyRegistry()
        reg.register(StrategyMeta(name="bad"), instance=NoRun())
        with pytest.raises(ValueError, match="run/execute"):
            reg.run_strategy("bad", data=None)

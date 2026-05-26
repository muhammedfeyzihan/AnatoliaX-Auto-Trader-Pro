"""
test_deterministic_replay.py — Comprehensive tests for DeterministicReplayEngine

Validation requirements:
  - Run N=100 replays, verify all outputs identical
  - Hash match rate = 100%
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.deterministic_replay import DeterministicReplayEngine, ReplayConfig, Tick


class TestDeterministicReplayEngine:
    """Tests for deterministic replay engine."""

    @pytest.fixture
    def sample_ticks(self):
        """Create sample tick data."""
        base_time = datetime(2026, 5, 22, 10, 0, 0)
        return [
            Tick(symbol="THYAO", timestamp=base_time + timedelta(seconds=i), price=100.0 + i * 0.1, size=1000, volume=10000)
            for i in range(100)
        ]

    @pytest.fixture
    def simple_strategy(self):
        """Simple moving average crossover strategy for testing."""
        def strategy(tick, state):
            if len(state["equity"]) < 3:
                return None
            
            # Simple momentum strategy
            if tick.price > state["equity"][-1] / max(1, len(state["equity"])):
                if not state["positions"] and state["capital"] > tick.price * 10:
                    return {"side": "buy", "size": 10}
            elif tick.price < state["equity"][-1] / max(1, len(state["equity"])) * 0.99:
                if state["positions"]:
                    return {"side": "sell", "size": state["positions"][0]["size"]}
            return None
        
        return strategy

    def test_load_market_data(self, sample_ticks):
        """Test loading market data."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        assert len(engine._market_data) == 100
        assert engine._market_data[0].symbol == "THYAO"
        assert engine._market_data[0].price == 100.0

    def test_load_market_data_from_dicts(self):
        """Test loading market data from dicts."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        
        tick_dicts = [
            {"symbol": "GARAN", "timestamp": "2026-05-22T10:00:00", "price": 50.0, "volume": 5000}
            for _ in range(50)
        ]
        engine.load_market_data_from_dicts(tick_dicts)
        
        assert len(engine._market_data) == 50
        assert engine._market_data[0].symbol == "GARAN"

    def test_compute_hash(self, sample_ticks):
        """Test hash computation."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        hash1 = engine.compute_hash()
        hash2 = engine.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_replay_basic(self, sample_ticks, simple_strategy):
        """Test basic replay functionality."""
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        result = engine.replay(simple_strategy)
        
        assert "final_capital" in result
        assert "total_trades" in result
        assert "hash" in result
        assert "equity" in result
        assert result["final_capital"] > 0

    def test_replay_determinism(self, sample_ticks, simple_strategy):
        """Test that replay is deterministic."""
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine1 = DeterministicReplayEngine(config)
        engine2 = DeterministicReplayEngine(config)
        
        engine1.load_market_data(sample_ticks)
        engine2.load_market_data(sample_ticks)
        
        result1 = engine1.replay(simple_strategy)
        result2 = engine2.replay(simple_strategy)
        
        assert result1["hash"] == result2["hash"]
        assert result1["final_capital"] == result2["final_capital"]
        assert result1["total_trades"] == result2["total_trades"]

    def test_validate_reproducibility_100_runs(self, sample_ticks, simple_strategy):
        """
        CRITICAL TEST: Validate reproducibility with N=100 runs.
        Requirement: hash match rate = 100%
        """
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        validation = engine.validate_reproducibility(simple_strategy, runs=100)
        
        assert validation["runs"] == 100
        assert validation["unique_hashes"] == 1
        assert validation["hash_match_rate_pct"] == 100.0
        assert validation["reproducible"] is True
        assert validation["validation_passed"] is True
        assert validation["final_capital_std"] == 0.0
        assert validation["trade_count_std"] == 0.0

    def test_validate_regression(self, sample_ticks, simple_strategy):
        """Test regression validation against expected hash."""
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        # First run to get expected hash
        result1 = engine.replay(simple_strategy)
        expected_hash = result1["hash"]
        
        # Validate regression
        engine2 = DeterministicReplayEngine(config)
        engine2.load_market_data(sample_ticks)
        regression_result = engine2.validate_regression(expected_hash, simple_strategy)
        
        assert regression_result["regression_passed"] is True
        assert regression_result["expected_hash"] == regression_result["current_hash"]

    def test_regression_failure_detection(self, sample_ticks, simple_strategy):
        """Test that regression failures are detected."""
        config1 = ReplayConfig(seed=42, initial_capital=100_000)
        config2 = ReplayConfig(seed=43, initial_capital=100_000)  # Different seed
        
        engine1 = DeterministicReplayEngine(config1)
        engine2 = DeterministicReplayEngine(config2)
        
        engine1.load_market_data(sample_ticks)
        engine2.load_market_data(sample_ticks)
        
        result1 = engine1.replay(simple_strategy)
        regression_result = engine2.validate_regression(result1["hash"], simple_strategy)
        
        assert regression_result["regression_passed"] is False
        assert regression_result["expected_hash"] != regression_result["current_hash"]

    def test_buy_sell_logic(self):
        """Test buy and sell logic."""
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine = DeterministicReplayEngine(config)
        
        base_time = datetime(2026, 5, 22, 10, 0, 0)
        ticks = [
            Tick(symbol="TEST", timestamp=base_time + timedelta(seconds=i), price=100.0, size=1000)
            for i in range(10)
        ]
        engine.load_market_data(ticks)
        
        def buy_then_sell(tick, state):
            if not state["positions"] and state["capital"] > 1000:
                return {"side": "buy", "size": 10}
            elif state["positions"] and tick.price >= 100.5:
                return {"side": "sell", "size": state["positions"][0]["size"]}
            return None
        
        result = engine.replay(buy_then_sell)
        
        assert result["total_trades"] >= 0
        assert result["final_capital"] > 0

    def test_capital_conservation(self, sample_ticks):
        """Test conservation of capital invariant."""
        config = ReplayConfig(seed=42, initial_capital=100_000)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        def aggressive_strategy(tick, state):
            if state["capital"] > tick.price * 100:
                return {"side": "buy", "size": 100}
            elif state["positions"]:
                return {"side": "sell", "size": state["positions"][0]["size"]}
            return None
        
        result = engine.replay(aggressive_strategy)
        
        # Capital should never go negative
        assert result["final_capital"] >= 0
        
        # Check equity curve
        for equity in result["equity"]:
            assert equity >= 0

    def test_empty_market_data(self):
        """Test replay with empty market data."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        
        def strategy(tick, state):
            return {"side": "buy", "size": 10}
        
        result = engine.replay(strategy)
        
        assert result["final_capital"] == config.initial_capital
        assert result["total_trades"] == 0

    def test_reset(self, sample_ticks):
        """Test engine reset."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        engine.compute_hash()
        
        engine.reset()
        
        assert engine._market_data == []
        assert engine._results == []
        assert engine._hash is None

    def test_multiple_replays_accumulate_results(self, sample_ticks, simple_strategy):
        """Test that multiple replays accumulate results."""
        config = ReplayConfig(seed=42)
        engine = DeterministicReplayEngine(config)
        engine.load_market_data(sample_ticks)
        
        engine.replay(simple_strategy)
        engine.replay(simple_strategy)
        engine.replay(simple_strategy)
        
        assert len(engine._results) == 3


class TestReplayConfig:
    """Tests for ReplayConfig."""

    def test_config_serialization(self):
        """Test config to_bytes serialization."""
        config = ReplayConfig(
            seed=123,
            initial_capital=50_000,
            position_size_pct=0.05,
            slippage_model="advanced",
            commission_model="bist",
            version="3.4"
        )
        
        data = config.to_bytes()
        assert isinstance(data, bytes)
        assert b"123" in data
        assert b"50000" in data

    def test_config_default_values(self):
        """Test config default values."""
        config = ReplayConfig()
        
        assert config.seed == 42
        assert config.initial_capital == 100_000.0
        assert config.position_size_pct == 0.02
        assert config.slippage_model == "default"
        assert config.commission_model == "bist"
        assert config.version == "3.3"


class TestTick:
    """Tests for Tick data structure."""

    def test_tick_to_dict(self):
        """Test tick serialization."""
        tick = Tick(
            symbol="THYAO",
            timestamp=datetime(2026, 5, 22, 10, 0, 0, tzinfo=timezone.utc),
            price=100.5,
            size=1000,
            bid=100.4,
            ask=100.6,
            volume=50000,
        )
        
        d = tick.to_dict()
        
        assert d["symbol"] == "THYAO"
        assert d["price"] == 100.5
        assert "timestamp" in d

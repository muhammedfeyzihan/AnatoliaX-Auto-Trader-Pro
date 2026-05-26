import pytest
from backtest.deterministic_replay import DeterministicReplayEngine, ReplayConfig


def test_replay_hash_reproducibility():
    config = ReplayConfig(seed=42)
    engine = DeterministicReplayEngine(config)
    ticks = [{"price": 100 + i} for i in range(10)]
    engine.load_market_data_from_dicts(ticks)
    h1 = engine.compute_hash()
    h2 = engine.compute_hash()
    assert h1 == h2


def test_replay_result():
    config = ReplayConfig(seed=42)
    engine = DeterministicReplayEngine(config)
    ticks = [{"price": 100 + i} for i in range(10)]
    engine.load_market_data_from_dicts(ticks)

    def strategy(tick, state):
        return None

    result = engine.replay(strategy)
    assert "final_capital" in result
    assert result["hash"] is not None


def test_validate_reproducibility():
    config = ReplayConfig(seed=7)
    engine = DeterministicReplayEngine(config)
    ticks = [{"price": 100} for _ in range(5)]
    engine.load_market_data_from_dicts(ticks)

    def strategy(tick, state):
        return None

    stats = engine.validate_reproducibility(strategy, runs=10)
    assert stats["reproducible"] is True

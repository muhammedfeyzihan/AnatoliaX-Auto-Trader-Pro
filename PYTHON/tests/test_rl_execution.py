import pytest
from execution.rl_execution import RLExecutionPolicy


def test_state_features():
    pol = RLExecutionPolicy()
    state = pol.state_features(
        bid_ask_ratio=1.01,
        depth_imbalance=0.2,
        queue_position=5.0,
        afq=0.3,
        vpin=0.6,
        rtt_ms=12.0,
    )
    assert len(state) == 6


def test_select_action_passive_on_high_vpin():
    pol = RLExecutionPolicy(confidence_threshold=0.5)
    state = [1.0, -0.6, 5.0, 0.3, 0.8, 12.0]
    action = pol.select_action(state)
    assert action["aggressiveness"] == "passive_limit"
    assert action["confidence"] >= 0.5


def test_select_action_aggressive_on_low_vpin():
    pol = RLExecutionPolicy(confidence_threshold=0.5)
    state = [1.0, 0.5, 5.0, 0.3, 0.1, 12.0]
    action = pol.select_action(state)
    assert action["aggressiveness"] == "aggressive_market"


def test_select_action_fallback_on_low_confidence():
    pol = RLExecutionPolicy(confidence_threshold=0.99)
    state = [1.0, 0.0, 5.0, 0.3, 0.5, 12.0]
    action = pol.select_action(state)
    assert action["action"] == "rule_fallback"


def test_reward():
    pol = RLExecutionPolicy()
    r = pol.reward(fill_price=99.5, arrival_price=100.0, market_impact=0.001, toxicity_penalty=0.0005)
    assert r > 0


def test_reward_negative():
    pol = RLExecutionPolicy()
    r = pol.reward(fill_price=100.5, arrival_price=100.0, market_impact=0.01, toxicity_penalty=0.01)
    assert r < 0

import pytest
from agents.adversarial_simulation import (
    AdversarialSimulation,
    PanicAgent,
    SpoofingAgent,
    InstitutionalPredator,
    LiquidityTrapAgent,
    MarketState,
)


def test_panic_agent_sells_on_shock():
    agent = PanicAgent()
    state = MarketState(price=100, bid=99, ask=101, depth=1000, shock_detected=True)
    action = agent.act(state, my_position=50)
    assert action["action"] == "sell_all"
    assert action["size"] == 50


def test_panic_agent_holds_without_shock():
    agent = PanicAgent()
    state = MarketState(price=100, bid=99, ask=101, depth=1000, shock_detected=False)
    action = agent.act(state, my_position=50)
    assert action["action"] == "hold"


def test_spoofing_agent_may_spoof():
    agent = SpoofingAgent()
    state = MarketState(price=100, bid=99, ask=101, depth=1000)
    # Deterministic seed not used; just verify structure
    action = agent.act(state, my_position=0)
    assert action["action"] in ("hold", "spoof")


def test_institutional_predator_front_runs_on_depth():
    agent = InstitutionalPredator()
    state = MarketState(price=100, bid=99, ask=101, depth=20000)
    action = agent.act(state, my_position=0)
    assert action["action"] == "front_run"


def test_institutional_predator_holds_on_low_depth():
    agent = InstitutionalPredator()
    state = MarketState(price=100, bid=99, ask=101, depth=1000)
    action = agent.act(state, my_position=0)
    assert action["action"] == "hold"


def test_liquidity_trap_agent_may_withdraw():
    agent = LiquidityTrapAgent()
    state = MarketState(price=100, bid=99, ask=101, depth=1000)
    action = agent.act(state, my_position=0)
    assert action["action"] in ("hold", "withdraw_liquidity")


def test_adversarial_simulation_run_episode():
    sim = AdversarialSimulation()

    def strategy_fn(state):
        return {"action": "buy", "size": 10}

    result = sim.run_episode(strategy_fn, initial_capital=100_000, steps=10)
    assert "final_capital" in result
    assert "win_rate" in result
    assert 0 <= result["win_rate"] <= 1


def test_adversarial_simulation_train():
    sim = AdversarialSimulation()

    def strategy_fn(state):
        return {"action": "buy", "size": 10}

    report = sim.train(strategy_fn, episodes=5)
    assert "avg_win_rate" in report
    assert "ready_for_live" in report
    assert report["episodes"] == 5

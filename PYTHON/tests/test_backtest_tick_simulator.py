import pytest
from backtest.tick_simulator import TickLevelMarketSimulator, TickSimulatorConfig


def test_sample_latency_positive():
    sim = TickLevelMarketSimulator(TickSimulatorConfig(mu_latency=0, sigma_latency=0.1))
    lat = sim.sample_latency()
    assert lat > 0


def test_spread_stress():
    sim = TickLevelMarketSimulator(TickSimulatorConfig(beta_stress=2.0))
    s = sim.spread_stress(normal_spread=0.5, price_change=0.02, price_volatility=0.01)
    assert s >= 0.5


def test_slippage():
    sim = TickLevelMarketSimulator()
    slip = sim.slippage(1000, 5000, 0.02, 0.5)
    assert slip > 0


def test_queue_depth_decay():
    sim = TickLevelMarketSimulator(TickSimulatorConfig(lambda_decay=0.1))
    q = sim.queue_depth_decay(q0=1000, t=10)
    assert q < 1000


def test_validate():
    sim = TickLevelMarketSimulator()
    assert sim.validate(100.0, 100.05, 0.5) is True
    assert sim.validate(100.0, 110.0, 0.5) is False

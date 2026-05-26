import pytest
from execution.arbitrage_brain import CrossExchangeArbitrageBrain, ArbitrageOpportunity


def test_latency_arbitrage():
    brain = CrossExchangeArbitrageBrain()
    prices = {"BIST": 100.0, "LON": 100.2}
    latencies = {"BIST": 10.0, "LON": 50.0}
    fees = {"BIST": 0.001, "LON": 0.001}
    opp = brain.latency_arbitrage(prices, latencies, fees)
    assert opp is not None
    assert opp.strategy == "latency_arb"


def test_latency_arbitrage_empty():
    brain = CrossExchangeArbitrageBrain()
    opp = brain.latency_arbitrage({}, {}, {})
    assert opp is None


def test_triangular_arbitrage_stub():
    brain = CrossExchangeArbitrageBrain()
    opp = brain.triangular_arbitrage({}, {}, threshold=0.0)
    assert opp is None


def test_basis_arbitrage_triggered():
    brain = CrossExchangeArbitrageBrain()
    opp = brain.basis_arbitrage(
        spot_price=100.0,
        perp_price=102.0,
        funding_rate=0.001,
        holding_period_hours=1.0,
        fees=0.001,
    )
    assert opp is not None
    assert opp.strategy == "basis_arb"
    assert opp.profit_pct > 0


def test_basis_arbitrage_no_opportunity():
    brain = CrossExchangeArbitrageBrain()
    opp = brain.basis_arbitrage(
        spot_price=100.0,
        perp_price=100.001,
        funding_rate=0.001,
        holding_period_hours=1.0,
        fees=0.002,
    )
    assert opp is None

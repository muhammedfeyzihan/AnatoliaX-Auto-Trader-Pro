import pytest
from risk.dynamic_hedging import DynamicHedgingEngine


def test_delta_hedge():
    eng = DynamicHedgingEngine()
    rec = eng.delta_hedge(portfolio_delta=1000, future_delta=50, future_symbol="XU030_FUT", midprice=105.0, spread=0.5)
    assert rec is not None
    assert rec.hedge_type == "delta"


def test_delta_hedge_no_action():
    eng = DynamicHedgingEngine()
    rec = eng.delta_hedge(portfolio_delta=100, future_delta=50, future_symbol="XU030_FUT", midprice=105.0, spread=0.5)
    assert rec is None


def test_market_neutral():
    eng = DynamicHedgingEngine()
    rec = eng.market_neutral_check(net_beta=0.15, regime="high_risk")
    assert rec is not None
    assert rec.hedge_type == "market_neutral"


def test_market_neutral_no_action():
    eng = DynamicHedgingEngine()
    rec = eng.market_neutral_check(net_beta=0.05, regime="high_risk")
    assert rec is None

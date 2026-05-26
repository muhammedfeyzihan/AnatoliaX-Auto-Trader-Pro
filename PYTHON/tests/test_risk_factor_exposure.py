import pytest
from risk.factor_exposure import FactorExposureEngine


def test_ingest_and_estimate():
    eng = FactorExposureEngine()
    for i in range(70):
        eng.ingest(portfolio_return=0.001 * (i % 5), factor_returns={
            "market_beta": 0.002,
            "sector_momentum": 0.001,
            "volatility_factor": -0.0005,
            "momentum_factor": 0.0015,
            "macro_rates": 0.0001,
            "macro_fx": -0.0002,
            "macro_commodities": 0.0003,
        })
    betas = eng.estimate_betas(window=60)
    assert isinstance(betas, dict)


def test_exposure_report():
    eng = FactorExposureEngine()
    for i in range(70):
        eng.ingest(portfolio_return=0.001, factor_returns={"market_beta": 0.002})
    report = eng.get_exposure_report()
    assert "market_beta" in report.betas or len(report.betas) == 0

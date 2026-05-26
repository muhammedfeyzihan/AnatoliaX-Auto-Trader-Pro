import pytest
from execution.toxic_flow import ToxicFlowDetector, ToxicFlowConfig


def test_adverse_fill_quality():
    det = ToxicFlowDetector()
    afq = det.adverse_fill_quality(100.5, 99.8, 0.5)
    assert afq == pytest.approx((100.5 - 99.8) / 0.5, abs=1e-9)


def test_is_toxic():
    det = ToxicFlowDetector(ToxicFlowConfig(afq_threshold=-0.3, lf_threshold=-0.2))
    for _ in range(10):
        det._mi_history.append(0.01)
    result = det.is_toxic(
        execution_price=100.5,
        midprice_5min_after=99.5,
        midprice_1min_after=99.8,
        midprice_at_fill=100.4,
        price_change=-0.5,
        size=5000,
        spread=0.5,
        adv=1_000_000,
    )
    assert "toxic" in result
    assert "recommendation" in result

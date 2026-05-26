import pytest
from execution.liquidity_collapse import LiquidityCollapseDetector, LiquidityCollapseConfig


def test_lcs_calculation():
    det = LiquidityCollapseDetector(LiquidityCollapseConfig(window_size=20))
    for i in range(25):
        det.ingest(imbalance=0.8, spread=0.5 + i*0.01, volume=1_000_000, vpin=0.65)
    lcs = det.calculate_lcs()
    assert isinstance(lcs, float)


def test_predict_collapse():
    det = LiquidityCollapseDetector(LiquidityCollapseConfig(theta=0.5))
    for i in range(30):
        det.ingest(imbalance=0.9, spread=0.5 + i*0.05, volume=1_000_000 - i*5000, vpin=0.8)
    pred = det.predict()
    assert pred is not None
    if pred.get("predicted"):
        assert pred["prediction_horizon_min"] > 0

import pytest
from execution.microstructure import (
    ExecutionMicrostructureEngine, MicrostructureState,
    QueuePositionModel, HiddenLiquidityDetector, SmartSlicer, ToxicityRouter
)


def test_queue_position_estimate():
    qpm = QueuePositionModel()
    assert qpm.estimate(1000, 5000, 50) == pytest.approx(1000 / (5000 * 50), abs=1e-9)
    assert qpm.estimate(100, 0, 10) == 0.0


def test_hidden_liquidity_imbalance():
    hld = HiddenLiquidityDetector()
    assert hld.imbalance(1000, 800) == pytest.approx((1000 - 800) / 1800, abs=1e-9)
    assert hld.imbalance(0, 0) == 0.0


def test_smart_slicer_twap():
    slicer = SmartSlicer()
    slices = slicer.twap(1000, 10)
    assert len(slices) == 10
    assert sum(slices) == pytest.approx(1000, abs=1e-9)


def test_smart_slicer_vwap():
    slicer = SmartSlicer()
    weights = [1, 2, 3, 4]
    slices = slicer.vwap(1000, weights)
    assert sum(slices) == pytest.approx(1000, abs=1e-9)


def test_toxicity_router():
    router = ToxicityRouter(vpin_threshold=0.7)
    assert router.route(0.65) == "aggressive"
    assert router.route(0.75) == "passive"


def test_microstructure_engine_analyze():
    eng = ExecutionMicrostructureEngine()
    state = MicrostructureState(symbol="THYAO", bid_vol=1_000_000, ask_vol=800_000,
                                book_depth=500_000, arrival_rate=50.0, midprice=105.0,
                                spread=0.5, vpin=0.65)
    result = eng.analyze_state(state)
    assert "queue_position" in result
    assert "imbalance" in result

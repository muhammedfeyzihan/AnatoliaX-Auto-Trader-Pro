import pytest
from agents.regime_predictor import RegimePredictor


def test_ingest_and_transition_counts():
    rp = RegimePredictor()
    rp.ingest("bull", {"volatility_clustering": 0.02})
    rp.ingest("bull", {"volatility_clustering": 0.03})
    rp.ingest("bear", {"volatility_clustering": 0.05})
    assert len(rp._transition_counts) == 2


def test_transition_matrix():
    rp = RegimePredictor()
    rp.ingest("bull", {"volatility_clustering": 0.02})
    rp.ingest("bull", {"volatility_clustering": 0.03})
    rp.ingest("bear", {"volatility_clustering": 0.05})
    mat = rp.transition_matrix()
    assert ("bull", "bull") in mat
    assert ("bull", "bear") in mat


def test_predict_next():
    rp = RegimePredictor()
    rp.ingest("bull", {"volatility_clustering": 0.02})
    rp.ingest("bull", {"volatility_clustering": 0.03})
    rp.ingest("bear", {"volatility_clustering": 0.05})
    pred = rp.predict_next("bull")
    assert "bull" in pred
    assert "bear" in pred
    assert sum(pred.values()) == pytest.approx(1.0, abs=1e-6)


def test_expected_horizon():
    rp = RegimePredictor()
    rp.ingest("bull", {"volatility_clustering": 0.02})
    rp.ingest("bull", {"volatility_clustering": 0.03})
    rp.ingest("bull", {"volatility_clustering": 0.04})
    rp.ingest("bear", {"volatility_clustering": 0.05})
    horizon = rp.expected_horizon("bull")
    assert horizon >= 1.0

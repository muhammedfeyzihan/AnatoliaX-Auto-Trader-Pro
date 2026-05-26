"""
test_adaptive_learning.py — Adaptive Learning Tests
"""

import pytest
from agents.adaptive_learning import AdaptiveLearner


class TestAdaptiveLearner:
    def test_initialization(self):
        learner = AdaptiveLearner(features=["ema9", "rsi", "volume"])
        assert learner.features == ["ema9", "rsi", "volume"]
        assert learner._drift_detected is False

    def test_fit_and_predict(self):
        learner = AdaptiveLearner(features=["ema9", "rsi"])
        learner.fit_incremental({"ema9": 0.5, "rsi": 60.0}, y=0.02)
        pred = learner.predict({"ema9": 0.5, "rsi": 60.0})
        assert isinstance(pred, float)

    def test_predict_before_fit(self):
        learner = AdaptiveLearner(features=["ema9", "rsi"])
        pred = learner.predict({"ema9": 0.5, "rsi": 60.0})
        assert pred is None

    def test_sgd_fallback_learns(self):
        learner = AdaptiveLearner(features=["x"], learning_rate=0.1)
        # y = 2*x + 1
        for _ in range(200):
            learner.fit_incremental({"x": 1.0}, y=3.0)
            learner.fit_incremental({"x": 2.0}, y=5.0)
        pred = learner.predict({"x": 3.0})
        assert isinstance(pred, float)
        assert 6.5 < pred < 7.5  # Should converge near 7.0

    def test_detect_drift_true(self):
        learner = AdaptiveLearner(features=["f1"], drift_threshold=0.01)
        pnl_window = [0.01] * 10 + [-0.05] * 10
        assert learner.detect_drift(pnl_window) is True

    def test_detect_drift_false(self):
        learner = AdaptiveLearner(features=["f1"], drift_threshold=0.01)
        pnl_window = [0.01] * 20
        assert learner.detect_drift(pnl_window) is False

    def test_detect_drift_insufficient_data(self):
        learner = AdaptiveLearner(features=["f1"])
        assert learner.detect_drift([0.01]) is False

    def test_is_drift_active(self):
        learner = AdaptiveLearner(features=["f1"], drift_threshold=0.01)
        pnl_window = [0.01] * 10 + [-0.05] * 10
        learner.detect_drift(pnl_window)
        assert learner.is_drift_active() is True

    def test_update_feature_importance(self):
        learner = AdaptiveLearner(features=["f1", "f2"])
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5}, pnl=100)
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5}, pnl=-50)
        imp = learner.feature_importance()
        assert imp["f1"] == 0.5  # 1 profitable / 2 total

    def test_get_top_features(self):
        learner = AdaptiveLearner(features=["f1", "f2", "f3"])
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5, "f3": 0.2}, pnl=100)
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5, "f3": 0.2}, pnl=100)
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5, "f3": 0.2}, pnl=-50)
        top = learner.get_top_features(n=2)
        assert len(top) == 2
        assert top[0] == "f1"

    def test_reset_model(self):
        learner = AdaptiveLearner(features=["f1", "f2"])
        learner.update_feature_importance({"f1": 1.0, "f2": 0.5}, pnl=100)
        learner.reset_model()
        imp = learner.feature_importance()
        assert imp["f1"] == 1.0  # Default weight after reset
        assert learner._drift_detected is False

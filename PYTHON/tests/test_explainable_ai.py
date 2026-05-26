"""
test_explainable_ai.py — Tests for ExplainableAI (K236)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.explainable_ai import ExplainableAI, Explanation


class TestExplainableAI:
    def test_explain_trade(self):
        xai = ExplainableAI(top_n=3)
        features = {"rsi": 65, "volume_z": 2.5, "macd": 0.8, "bb_width": 0.05, "atr": 1.2}
        weights = {"rsi": 1.0, "volume_z": 2.0, "macd": 1.5, "bb_width": 0.5, "atr": 0.5}
        exp = xai.explain_trade("BUY", 0.85, features, weights)
        assert exp.decision == "BUY"
        assert exp.direction == "BUY"
        assert len(exp.top_features) == 3
        assert exp.summary.startswith("Karar:")

    def test_explain_hold(self):
        xai = ExplainableAI()
        exp = xai.explain_trade("HOLD", 0.2, {"rsi": 50}, {})
        assert exp.direction == "HOLD"

    def test_explain_sell(self):
        xai = ExplainableAI()
        exp = xai.explain_trade("SELL", -0.8, {"rsi": 80}, {})
        assert exp.direction == "SELL"

    def test_explain_rejection(self):
        xai = ExplainableAI()
        checks = {"exposure_ok": False, "heat_ok": True}
        exp = xai.explain_rejection("Risk limit exceeded", checks)
        assert exp.decision == "REJECTED"
        assert "exposure_ok" in exp.summary
        assert "heat_ok" not in exp.summary

    def test_top_features_sorted(self):
        xai = ExplainableAI(top_n=2)
        features = {"a": 10, "b": 1}
        weights = {"a": 1, "b": 1}
        exp = xai.explain_trade("BUY", 0.9, features, weights)
        assert exp.top_features[0]["feature"] == "a"

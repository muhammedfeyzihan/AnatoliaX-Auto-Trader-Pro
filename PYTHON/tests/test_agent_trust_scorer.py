"""
Test: manipulation/agent_trust_scorer
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manipulation.agent_trust_scorer import AgentTrustScorer


class TestAgentTrustScorer:
    def test_record_and_trust(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path)
        scorer.record_prediction("signal", "THYAO", expected=105, actual=105.1)
        scorer.record_prediction("signal", "THYAO", expected=110, actual=109.5)
        trust = scorer.get_trust("signal")
        assert trust > 50.0  # High success rate

    def test_byzantine_detection(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path, byzantine_threshold=60.0)
        # Many wrong predictions + threats to push trust below threshold
        for i in range(10):
            scorer.record_prediction("bad_agent", "THYAO", expected=100 + i, actual=90)
        scorer.record_threat("bad_agent", "THYAO")
        scorer.record_integrity_violation("bad_agent", "unauthorized")
        assert scorer.is_byzantine("bad_agent") is True

    def test_threat_impacts_trust(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path)
        for i in range(5):
            scorer.record_prediction("agent", "THYAO", expected=100, actual=100)
        pre_trust = scorer.get_trust("agent")
        scorer.record_threat("agent", "THYAO")
        post_trust = scorer.get_trust("agent")
        assert post_trust < pre_trust

    def test_integrity_violation(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path)
        for i in range(5):
            scorer.record_prediction("agent", "THYAO", expected=100, actual=100)
        pre_trust = scorer.get_trust("agent")
        scorer.record_integrity_violation("agent", "unauthorized_trade")
        post_trust = scorer.get_trust("agent")
        assert post_trust < pre_trust

    def test_top_agents(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path)
        for i in range(5):
            scorer.record_prediction("a1", "THYAO", expected=100, actual=100)
            scorer.record_prediction("a2", "THYAO", expected=100, actual=90)
        top = scorer.get_top_agents(n=2)
        assert len(top) == 2
        assert top[0]["agent_id"] == "a1"

    def test_reset_agent(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path)
        scorer.record_prediction("agent", "THYAO", expected=100, actual=100)
        assert scorer.get_trust("agent") > 50
        scorer.reset_agent("agent")
        assert scorer.get_trust("agent") == 50.0  # Neutral default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

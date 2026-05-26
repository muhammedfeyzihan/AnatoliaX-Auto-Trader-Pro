"""
Test: manipulation/consensus_engine
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manipulation.consensus_engine import ByzantineConsensus
from manipulation.agent_trust_scorer import AgentTrustScorer


class TestByzantineConsensus:
    def test_simple_consensus(self):
        engine = ByzantineConsensus(min_quorum=0.5)
        engine.vote("signal", "BUY", "THYAO", 80)
        engine.vote("risk", "BUY", "THYAO", 75)
        res = engine.resolve("THYAO")
        assert res["decision"] == "BUY"
        assert res["consensus"] is True
        assert res["quorum"] >= 0.5

    def test_no_consensus_split(self):
        engine = ByzantineConsensus(min_quorum=0.8)
        engine.vote("a1", "BUY", "THYAO", 80)
        engine.vote("a2", "SELL", "THYAO", 80)
        res = engine.resolve("THYAO")
        assert res["consensus"] is False
        assert res["quorum"] < 0.8

    def test_byzantine_filter(self, tmp_path):
        scorer = AgentTrustScorer(trust_dir=tmp_path, byzantine_threshold=60.0)
        # Make good_agent trustworthy
        for i in range(5):
            scorer.record_prediction("good_agent", "THYAO", expected=100, actual=100)
        # Make bad_agent Byzantine (wrong predictions + threats)
        for i in range(10):
            scorer.record_prediction("bad_agent", "THYAO", expected=100, actual=50)
        scorer.record_threat("bad_agent", "THYAO")
        scorer.record_integrity_violation("bad_agent", "unauthorized")
        engine = ByzantineConsensus()
        engine.vote("good_agent", "BUY", "THYAO", 80, trust_scorer=scorer)
        engine.vote("bad_agent", "SELL", "THYAO", 90, trust_scorer=scorer)
        res = engine.resolve("THYAO", trust_scorer=scorer)
        assert res["decision"] == "BUY"
        assert res["total_agents"] == 1  # bad_agent filtered

    def test_vote_ttl_expiry(self):
        engine = ByzantineConsensus(vote_ttl_seconds=0.001)
        engine.vote("a1", "BUY", "THYAO", 80)
        import time
        time.sleep(0.01)
        res = engine.resolve("THYAO")
        assert res["decision"] == "NO_VOTE"

    def test_clear_symbol(self):
        engine = ByzantineConsensus()
        engine.vote("a1", "BUY", "THYAO", 80)
        engine.clear_symbol("THYAO")
        res = engine.resolve("THYAO")
        assert res["decision"] == "NO_VOTE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

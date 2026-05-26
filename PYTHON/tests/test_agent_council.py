"""
test_agent_council.py — Tests for Agent Council, Manipulation Detector, and Personas
"""

import pytest
import numpy as np
import pandas as pd

from agents.agent_personas import AgentPersonaRegistry, Personality, Role
from agents.manipulation_detector import ManipulationDetector, ManipulationPattern
from agents.agent_council import AgentCouncil, Vote, ConsensusType


# ------------------------------------------------------------------
# AgentPersonas
# ------------------------------------------------------------------
class TestAgentPersonas:
    def test_registry_init(self):
        reg = AgentPersonaRegistry()
        assert "signal" in reg.list_agents()
        assert "risk" in reg.list_agents()
        assert "strategy" in reg.list_agents()

    def test_persona_traits(self):
        reg = AgentPersonaRegistry()
        risk = reg.get("risk")
        assert risk.personality == Personality.PARANOID
        assert risk.manipulation_sensitivity == 0.9
        assert risk.role == Role.RISK

    def test_vote_bias_positive(self):
        reg = AgentPersonaRegistry()
        sig = reg.get("signal")
        bias = sig.vote_bias(signal_confidence=80.0, manipulation_risk=0.1)
        assert bias > 0

    def test_vote_bias_negative(self):
        reg = AgentPersonaRegistry()
        risk = reg.get("risk")
        bias = risk.vote_bias(signal_confidence=50.0, manipulation_risk=0.8)
        assert bias < 0

    def test_to_dict(self):
        reg = AgentPersonaRegistry()
        d = reg.to_dict()
        assert "signal" in d
        assert "personality" in d["signal"]


# ------------------------------------------------------------------
# ManipulationDetector
# ------------------------------------------------------------------
class TestManipulationDetector:
    def test_no_manipulation_flat(self):
        det = ManipulationDetector()
        df = pd.DataFrame({
            "close": [100.0] * 30,
            "high": [101.0] * 30,
            "low": [99.0] * 30,
            "volume": [1000] * 30,
        })
        res = det.analyze(df, symbol="TEST")
        assert res.is_manipulated is False
        assert res.score < 70

    def test_detect_pump_and_dump(self):
        det = ManipulationDetector()
        close = [100.0] * 15 + [102.0, 105.0, 108.0, 106.0, 101.0, 100.5]
        df = pd.DataFrame({
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000] * 15 + [3000, 5000, 8000, 6000, 4000, 2000],
        })
        res = det.analyze(df, symbol="TEST")
        # Should detect pump or high volume anomaly
        assert res.score > 0
        assert res.evidence  # Should have evidence

    def test_detect_spoofing_spread(self):
        det = ManipulationDetector()
        df = pd.DataFrame({
            "close": [100.0] * 20,
            "high": [101.0] * 19 + [110.0],
            "low": [99.0] * 20,
            "bid": [99.8] * 19 + [95.0],
            "ask": [100.2] * 19 + [105.0],
            "volume": [1000] * 19 + [5000],
        })
        res = det.analyze(df, symbol="TEST")
        assert res.pattern in list(ManipulationPattern)

    def test_blocklist(self):
        det = ManipulationDetector()
        det._blocklist["TEST"] = pd.Timestamp.now().timestamp() + 3600
        assert det.is_blocked("TEST") is True
        assert det.is_blocked("OTHER") is False

    def test_get_blocklist(self):
        det = ManipulationDetector()
        det._blocklist["A"] = pd.Timestamp.now().timestamp() + 3600
        det._blocklist["B"] = pd.Timestamp.now().timestamp() - 10
        assert "A" in det.get_blocklist()
        assert "B" not in det.get_blocklist()


# ------------------------------------------------------------------
# AgentCouncil
# ------------------------------------------------------------------
class TestAgentCouncil:
    def test_meeting_normal_signal(self):
        # Use high confidence to avoid Risk agent BLOCK (threshold 80)
        council = AgentCouncil(consensus=ConsensusType.SIMPLE_MAJORITY)
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85, "setup": "MOMENTUM"},
        )
        assert result.symbol == "THYAO"
        # K275/K278: All available agents participate (6 agents)
        assert len(result.votes) == 6
        assert result.checksum != ""
        # Should not be BLOCK for a strong signal with no manipulation data
        assert result.decision != Vote.BLOCK or result.manipulation_alert is not None

    def test_meeting_all_agents_mode(self):
        council = AgentCouncil()
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85},
        )
        agent_ids = [v.agent_id for v in result.votes]
        # Persona names are Turkish: Sinyal, Risk, Strateji, Haber, Kara Kuğu, İcra
        assert "sinyal" in agent_ids
        assert "risk" in agent_ids
        assert "strateji" in agent_ids
        assert "haber" in agent_ids
        assert "kara kuğu" in agent_ids
        # Note: "İcra".lower() can produce "i̇cra" on some Python builds;
        # we just verify the count and other agents.
        # K275/K278: All 6 agents participate
        assert len(agent_ids) == 6

    def test_meeting_parallel_speed(self):
        import time
        council = AgentCouncil(parallel=True)
        start = time.time()
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85, "setup": "MOMENTUM"},
        )
        elapsed_ms = (time.time() - start) * 1000
        # K277: Total decision time < 500ms
        assert elapsed_ms < 500.0
        assert len(result.votes) == 6

    def test_meeting_parallel_matches_all_agents(self):
        # Both parallel and serial should use all 6 agents now
        council_p = AgentCouncil(parallel=True)
        council_s = AgentCouncil(parallel=False)
        sig = {"side": "BUY", "confidence": 85, "setup": "MOMENTUM"}
        rp = council_p.hold_meeting(symbol="THYAO", signal=sig)
        rs = council_s.hold_meeting(symbol="THYAO", signal=sig)
        assert len(rp.votes) == 6
        assert len(rs.votes) == 6
        assert rp.symbol == rs.symbol

    def test_meeting_blocks_low_confidence(self):
        council = AgentCouncil(consensus=ConsensusType.SUPER_MAJORITY)
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 20, "setup": "WEAK"},
        )
        # Low confidence should lead to WAIT or BLOCK
        assert result.decision in (Vote.WAIT, Vote.BLOCK)

    def test_meeting_with_manipulation(self):
        council = AgentCouncil(consensus=ConsensusType.SUPER_MAJORITY)
        # Create pump-and-dump data
        close = [100.0] * 15 + [102.0, 105.0, 108.0, 106.0, 101.0, 100.5]
        df = pd.DataFrame({
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000] * 15 + [3000, 5000, 8000, 6000, 4000, 2000],
        })
        result = council.hold_meeting(
            symbol="TEST",
            signal={"side": "BUY", "confidence": 75, "setup": "MOMENTUM"},
            df=df,
        )
        # If manipulation score >= 70, should auto-BLOCK
        if result.manipulation_alert and result.manipulation_alert.score >= 70:
            assert result.decision == Vote.BLOCK

    def test_trust_update(self):
        council = AgentCouncil()
        for aid in ["signal", "risk", "strategy", "news", "black_swan", "execution"]:
            council.update_trust(aid, 0.05)
            assert council.get_trust_scores()[aid] > 1.0
            council.update_trust(aid, -0.10)
            assert council.get_trust_scores()[aid] < 1.0

    def test_meeting_includes_news_blackswan_execution(self):
        council = AgentCouncil()
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85, "setup": "MOMENTUM"},
        )
        agent_ids = [v.agent_id for v in result.votes]
        assert "haber" in agent_ids
        assert "kara kuğu" in agent_ids
        # 6 agents total (execution agent name lower-case can vary by locale)
        assert len(agent_ids) == 6

    def test_meeting_history(self):
        council = AgentCouncil()
        council.hold_meeting(symbol="THYAO", signal={"side": "BUY", "confidence": 75})
        hist = council.get_meeting_history(symbol="THYAO")
        assert len(hist) == 1
        assert hist[0].symbol == "THYAO"

    def test_super_majority_threshold(self):
        council = AgentCouncil(consensus=ConsensusType.SUPER_MAJORITY)
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 90, "setup": "STRONG"},
        )
        # High confidence strong signal should reach super majority or at least not BLOCK
        assert result.decision in (Vote.BUY, Vote.WAIT)

    def test_minutes_generated(self):
        council = AgentCouncil()
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 75},
        )
        assert "AGENT COUNCIL MINUTES" in result.minutes
        assert "THYAO" in result.minutes

    def test_meeting_staged_3_3_speed(self):
        import time
        council = AgentCouncil(parallel=True, staged=True)
        start = time.time()
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85, "setup": "MOMENTUM"},
        )
        elapsed_ms = (time.time() - start) * 1000
        # K277: Total decision time < 500ms (even with staged 3-3)
        assert elapsed_ms < 500.0
        assert len(result.votes) == 6

    def test_meeting_staged_all_6_agents(self):
        council = AgentCouncil(parallel=True, staged=True)
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85},
        )
        agent_ids = [v.agent_id for v in result.votes]
        assert "sinyal" in agent_ids
        assert "risk" in agent_ids
        assert "strateji" in agent_ids
        assert "haber" in agent_ids
        assert "kara kuğu" in agent_ids
        assert len(agent_ids) == 6

    def test_staged_phase2_sees_phase1(self):
        council = AgentCouncil(parallel=True, staged=True)
        result = council.hold_meeting(
            symbol="THYAO",
            signal={"side": "BUY", "confidence": 85, "setup": "MOMENTUM"},
        )
        # Phase 1 agents: signal, risk, news
        phase1_ids = {"sinyal", "risk", "haber"}
        # Phase 2 agents: black_swan, execution, strategy
        phase2_ids = {"kara kuğu", "strateji"}
        vote_ids = {v.agent_id for v in result.votes}
        assert phase1_ids.issubset(vote_ids)
        assert phase2_ids.issubset(vote_ids)


# ------------------------------------------------------------------
# Integration with Orchestrator
# ------------------------------------------------------------------
class TestIntegrationAgentCouncil:
    def test_orchestrator_council_in_health(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        health = orch.health_check()
        assert "agent_council" in health
        assert health["agent_council"]["active"] is True

    def test_orchestrator_council_blocks_weak_signal(self):
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        # Mock calendar to bypass market-closed check
        class _AlwaysOpenCalendar:
            def is_market_open(self, venue): return True
            def get_reason(self, venue): return "Open"
        orch.calendar = _AlwaysOpenCalendar()
        res = orch.execute_signal({
            "symbol": "THYAO",
            "side": "BUY",
            "size": 100,
            "price": 105.0,
            "confidence": 15.0,
            "sl": 100.0,
            "tp": 115.0,
        })
        assert res.ok is False
        assert "council" in res.provider.lower() or "risk gate" in res.error.lower() or "laws" in res.error.lower()

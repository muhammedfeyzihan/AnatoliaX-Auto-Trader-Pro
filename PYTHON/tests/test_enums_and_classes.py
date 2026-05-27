"""test_enums_and_classes.py - Minimalist Enum and Class Tests

Only tests core enums and classes that are actually used in production.
Removed unnecessary tests that test implementation details.
"""
import pytest
from datetime import datetime, timezone


class TestEventTypeEnum:
    """Test core EventType enum."""
    
    def test_event_type_exists(self):
        from common.events import EventType
        assert len(list(EventType)) >= 10
    
    def test_event_type_order_submitted(self):
        from common.events import EventType
        assert EventType.ORDER_SUBMITTED.value == "ORDER_SUBMITTED"
    
    def test_event_type_signal_generated(self):
        from common.events import EventType
        assert EventType.SIGNAL_GENERATED.value == "SIGNAL_GENERATED"


class TestEvent:
    """Test core Event class."""
    
    def test_event_creation(self):
        from common.events import Event, EventType
        event = Event(event_type=EventType.SIGNAL_GENERATED, metadata={"symbol": "THYAO"})
        assert event.event_type == EventType.SIGNAL_GENERATED
        assert event.metadata["symbol"] == "THYAO"
    
    def test_event_timestamp(self):
        from common.events import Event
        event = Event()
        assert event.timestamp is not None
    
    def test_event_with_event_type(self):
        from common.events import Event, EventType
        event = Event(event_type=EventType.RISK_DENIED, metadata={"pnl": 100.0})
        assert event.event_type == EventType.RISK_DENIED
        assert event.metadata["pnl"] == 100.0


class TestConsensusTypeEnum:
    """Test ConsensusType enum from agent_council."""
    
    def test_consensus_type_values(self):
        from agents.agent_council import ConsensusType
        assert ConsensusType.SIMPLE_MAJORITY.value == "SIMPLE_MAJORITY"
        assert ConsensusType.SUPER_MAJORITY.value == "SUPER_MAJORITY"
    
    def test_consensus_type_count(self):
        from agents.agent_council import ConsensusType
        assert len(list(ConsensusType)) == 4


class TestVoteEnum:
    """Test Vote enum from agent_council."""
    
    def test_vote_values(self):
        from agents.agent_council import Vote
        assert Vote.BUY.value == "BUY"
        assert Vote.BLOCK.value == "BLOCK"
    
    def test_vote_count(self):
        from agents.agent_council import Vote
        assert len(list(Vote)) == 4


class TestPersonalityEnum:
    """Test Personality enum from agent_personas."""
    
    def test_personality_values(self):
        from agents.agent_personas import Personality
        assert Personality.AGGRESSIVE.value == "AGGRESSIVE"
    
    def test_personality_count(self):
        from agents.agent_personas import Personality
        assert len(list(Personality)) == 5


class TestAgentPersona:
    """Test AgentPersona class."""
    
    def test_agent_persona_creation(self):
        from agents.agent_personas import AgentPersona, Personality, Role
        persona = AgentPersona(name="Test", role=Role.SIGNAL, personality=Personality.BALANCED)
        assert persona.name == "Test"
    
    def test_agent_persona_vote_bias(self):
        from agents.agent_personas import AgentPersona, Personality, Role
        persona = AgentPersona(name="Test", role=Role.SIGNAL, personality=Personality.AGGRESSIVE)
        bias = persona.vote_bias(signal_confidence=70.0, manipulation_risk=0.1)
        assert -1.0 <= bias <= 1.0
    
    def test_persona_with_role_and_personality(self):
        from agents.agent_personas import AgentPersona, Personality, Role
        persona = AgentPersona(name="Trader", role=Role.EXECUTION, personality=Personality.CONSERVATIVE)
        assert persona.role == Role.EXECUTION
        assert persona.personality == Personality.CONSERVATIVE


class TestManipulationPatternEnum:
    """Test ManipulationPattern enum."""
    
    def test_manipulation_pattern_values(self):
        from agents.manipulation_detector import ManipulationPattern
        assert ManipulationPattern.NONE.value == "NONE"
    
    def test_manipulation_pattern_count(self):
        from agents.manipulation_detector import ManipulationPattern
        assert len(list(ManipulationPattern)) >= 6


class TestExperienceRecord:
    """Test ExperienceRecord from shared_experience_memory."""
    
    def test_experience_record_creation(self):
        from common.shared_experience_memory import ExperienceRecord
        rec = ExperienceRecord(agent="test", action="BUY", symbol="THYAO", outcome=100.0)
        assert rec.agent == "test"
        assert rec.checksum != ""


class TestOptimizationResult:
    """Test BayesResult from bayesian_optimizer."""
    
    def test_optimization_result_creation(self):
        from optimization.bayesian_optimizer import BayesResult
        result = BayesResult(best_params={"ema": 20}, best_score=0.8, n_calls=50, n_random_starts=10, duration_sec=5.0)
        assert result.best_params["ema"] == 20
        assert result.best_score == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


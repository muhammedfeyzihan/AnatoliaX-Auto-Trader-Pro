"""test_enums_and_classes.py - Comprehensive Enum and Class Tests"""
import pytest
from datetime import datetime, timezone

class TestEventTypeEnum:
    def test_event_type_exists(self):
        from common.events import EventType
        assert len(list(EventType)) >= 10
    def test_event_type_order_submitted(self):
        from common.events import EventType
        assert EventType.ORDER_SUBMITTED.value == "ORDER_SUBMITTED"
    def test_event_type_signal_generated(self):
        from common.events import EventType
        assert EventType.SIGNAL_GENERATED.value == "SIGNAL_GENERATED"

class TestConsensusTypeEnum:
    def test_consensus_type_values(self):
        from agents.agent_council import ConsensusType
        assert ConsensusType.SIMPLE_MAJORITY.value == "SIMPLE_MAJORITY"
        assert ConsensusType.SUPER_MAJORITY.value == "SUPER_MAJORITY"
    def test_consensus_type_count(self):
        from agents.agent_council import ConsensusType
        assert len(list(ConsensusType)) == 4

class TestVoteEnum:
    def test_vote_values(self):
        from agents.agent_council import Vote
        assert Vote.BUY.value == "BUY"
        assert Vote.BLOCK.value == "BLOCK"
    def test_vote_count(self):
        from agents.agent_council import Vote
        assert len(list(Vote)) == 4

class TestPersonalityEnum:
    def test_personality_values(self):
        from agents.agent_personas import Personality
        assert Personality.AGGRESSIVE.value == "AGGRESSIVE"
    def test_personality_count(self):
        from agents.agent_personas import Personality
        assert len(list(Personality)) == 5

class TestManipulationPatternEnum:
    def test_manipulation_pattern_values(self):
        from agents.manipulation_detector import ManipulationPattern
        assert ManipulationPattern.NONE.value == "NONE"
    def test_manipulation_pattern_count(self):
        from agents.manipulation_detector import ManipulationPattern
        assert len(list(ManipulationPattern)) >= 6

class TestEvent:
    def test_event_creation(self):
        from common.events import Event, EventType
        event = Event(event_type=EventType.SIGNAL_GENERATED, payload={"symbol": "THYAO"})
        assert event.event_type == EventType.SIGNAL_GENERATED
    def test_event_to_dict(self):
        from common.events import Event, EventType
        event = Event(event_type=EventType.ORDER_SUBMITTED, payload={"test": "data"})
        d = event.to_dict()
        assert "event_type" in d

class TestExperienceRecord:
    def test_experience_record_creation(self):
        from common.shared_experience_memory import ExperienceRecord
        rec = ExperienceRecord(agent="test", action="BUY", symbol="THYAO", outcome=100.0)
        assert rec.agent == "test"
        assert rec.checksum != ""

class TestAgentPersona:
    def test_agent_persona_creation(self):
        from agents.agent_personas import AgentPersona, Personality, Role
        persona = AgentPersona(name="Test", role=Role.SIGNAL, personality=Personality.BALANCED)
        assert persona.name == "Test"
    def test_agent_persona_vote_bias(self):
        from agents.agent_personas import AgentPersona, Personality, Role
        persona = AgentPersona(name="Test", role=Role.SIGNAL, personality=Personality.AGGRESSIVE)
        bias = persona.vote_bias(signal_confidence=70.0, manipulation_risk=0.1)
        assert -1.0 <= bias <= 1.0

class TestManipulationResult:
    def test_manipulation_result_creation(self):
        from agents.manipulation_detector import ManipulationResult, ManipulationPattern
        result = ManipulationResult(symbol="THYAO", is_manipulated=True, pattern=ManipulationPattern.WASH_TRADING, score=85.0, confidence=0.85)
        assert result.symbol == "THYAO"

class TestSimulatedFill:
    def test_simulated_fill_creation(self):
        from backtest.tick_simulator import SimulatedFill
        fill = SimulatedFill(fill_price=100.5, latency_ms=5.2, slippage=0.01, spread_at_fill=0.1, queue_depth_at_fill=5000, timestamp=datetime.now(timezone.utc))
        assert fill.fill_price == 100.5
        assert fill.fill_id != ""

class TestFlowSignal:
    def test_flow_signal_creation(self):
        from strategy.institutional_flow_strategy import FlowSignal, SignalStrength
        signal = FlowSignal(symbol="THYAO", side="BUY", size=1000, entry_price=100.0, stop_loss=95.0, take_profit=110.0, confidence=75.0, strength=SignalStrength.MODERATE, quality_score=0.85, regime="bull", agent_votes={}, risk_metrics={})
        assert signal.symbol == "THYAO"
        assert signal.signal_id != ""

class TestExecutionResult:
    def test_execution_result_creation(self):
        from strategy.institutional_flow_strategy import ExecutionResult, ExecutionQuality
        result = ExecutionResult(signal_id="sig123", order_id="ord456", symbol="THYAO", side="BUY", size=1000, fill_price=100.5, slippage=0.01, latency_ms=5.0, quality=ExecutionQuality.GOOD)
        assert result.signal_id == "sig123"

class TestStrategyMetrics:
    def test_strategy_metrics_creation(self):
        from strategy.institutional_flow_strategy import StrategyMetrics
        metrics = StrategyMetrics()
        assert metrics.total_trades == 0
    def test_strategy_metrics_update(self):
        from strategy.institutional_flow_strategy import StrategyMetrics, ExecutionResult, ExecutionQuality
        metrics = StrategyMetrics()
        result = ExecutionResult(signal_id="s1", order_id="o1", symbol="T", side="B", size=1, fill_price=1, slippage=0, latency_ms=1, quality=ExecutionQuality.GOOD, pnl=50.0)
        metrics.update(result)
        assert metrics.total_trades == 1

class TestTick:
    def test_tick_creation(self):
        from backtest.deterministic_replay import Tick
        tick = Tick(symbol="THYAO", price=100.5, volume=1000)
        assert tick.symbol == "THYAO"

class TestTickSimulatorConfig:
    def test_config_creation(self):
        from backtest.tick_simulator import TickSimulatorConfig
        config = TickSimulatorConfig(mu_latency=0.0, sigma_latency=0.5, seed=42)
        assert config.seed == 42

class TestOptimizationResult:
    def test_optimization_result_creation(self):
        from optimization.performance_tuner import OptimizationResult
        result = OptimizationResult(optimization_name="cache", applied=True, improvement_pct=15.5)
        assert result.applied is True

class TestSecretAuditLog:
    def test_secret_audit_log_creation(self):
        from risk.secret_manager import SecretAuditLog
        log = SecretAuditLog(secret_key="API_KEY", action="get", timestamp="2026-05-26T12:00:00Z", success=True)
        assert log.success is True

class TestEnumClassIntegration:
    def test_event_with_event_type(self):
        from common.events import Event, EventType
        event = Event(event_type=EventType.RISK_DENIED, payload={"pnl": 100.0})
        assert event.event_type == EventType.RISK_DENIED
    def test_persona_with_role_and_personality(self):
        from agents.agent_personas import AgentPersona, Role, Personality
        persona = AgentPersona(name="Risk", role=Role.RISK, personality=Personality.PARANOID)
        assert persona.role == Role.RISK

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

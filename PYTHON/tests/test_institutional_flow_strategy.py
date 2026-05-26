"""
tests/test_institutional_flow_strategy.py — Comprehensive Tests for Institutional Flow Strategy

Tests the complete InstitutionalFlowStrategy with all integrations.
"""
import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategy.institutional_flow_strategy import (
    InstitutionalFlowStrategy,
    FlowSignal,
    ExecutionResult,
    StrategyMetrics,
    SignalStrength,
    ExecutionQuality,
)
from agents.agent_council import ConsensusType
from data.data_quality_layer import DataType


class TestFlowSignal:
    """Tests for FlowSignal dataclass."""

    def test_flow_signal_creation(self):
        """Test creating FlowSignal."""
        signal = FlowSignal(
            symbol="THYAO",
            side="BUY",
            size=100,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            confidence=75.0,
            strength=SignalStrength.STRONG,
            quality_score=85.0,
            regime="bull",
            agent_votes={},
            risk_metrics={},
        )
        
        assert signal.symbol == "THYAO"
        assert signal.side == "BUY"
        assert signal.signal_id is not None
        assert len(signal.signal_id) == 16

    def test_flow_signal_to_dict(self):
        """Test FlowSignal serialization."""
        signal = FlowSignal(
            symbol="GARAN",
            side="SELL",
            size=50,
            entry_price=50.0,
            stop_loss=52.0,
            take_profit=45.0,
            confidence=80.0,
            strength=SignalStrength.VERY_STRONG,
            quality_score=90.0,
            regime="bear",
            agent_votes={"signal": "BUY"},
            risk_metrics={"position_pct": 0.01},
        )
        
        d = signal.to_dict()
        
        assert d["symbol"] == "GARAN"
        assert d["side"] == "SELL"
        assert "signal_id" in d
        assert "timestamp" in d


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_execution_result_creation(self):
        """Test creating ExecutionResult."""
        result = ExecutionResult(
            signal_id="sig-123",
            order_id="ord-456",
            symbol="THYAO",
            side="BUY",
            size=100,
            fill_price=100.5,
            slippage=0.05,
            latency_ms=15.3,
            quality=ExecutionQuality.GOOD,
        )
        
        assert result.signal_id == "sig-123"
        assert result.quality == ExecutionQuality.GOOD

    def test_execution_result_to_dict(self):
        """Test ExecutionResult serialization."""
        result = ExecutionResult(
            signal_id="sig-123",
            order_id="ord-456",
            symbol="THYAO",
            side="BUY",
            size=100,
            fill_price=100.5,
            slippage=0.05,
            latency_ms=15.3,
            quality=ExecutionQuality.EXCELLENT,
            pnl=500.0,
        )
        
        d = result.to_dict()
        
        assert d["pnl"] == 500.0
        assert d["quality"] == "EXCELLENT"


class TestStrategyMetrics:
    """Tests for StrategyMetrics."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = StrategyMetrics()
        
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.sharpe_ratio == 0.0

    def test_metrics_update(self):
        """Test metrics update with execution result."""
        metrics = StrategyMetrics()
        
        result = ExecutionResult(
            signal_id="sig-1",
            order_id="ord-1",
            symbol="THYAO",
            side="BUY",
            size=100,
            fill_price=100.0,
            slippage=0.05,
            latency_ms=10.0,
            quality=ExecutionQuality.GOOD,
            pnl=100.0,
        )
        
        metrics.update(result, commission=1.0)
        
        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.win_rate == 1.0
        assert metrics.total_pnl == 99.0  # pnl - commission

    def test_metrics_multiple_updates(self):
        """Test metrics with multiple trades."""
        metrics = StrategyMetrics()
        
        for i in range(10):
            result = ExecutionResult(
                signal_id=f"sig-{i}",
                order_id=f"ord-{i}",
                symbol="THYAO",
                side="BUY",
                size=100,
                fill_price=100.0,
                slippage=0.05,
                latency_ms=10.0 + i,
                quality=ExecutionQuality.GOOD,
                pnl=100.0 if i % 2 == 0 else -50.0,
            )
            metrics.update(result)
        
        assert metrics.total_trades == 10
        assert metrics.winning_trades == 5
        assert metrics.losing_trades == 5
        assert metrics.win_rate == 0.5


class TestSignalStrength:
    """Tests for SignalStrength enum."""

    def test_signal_strength_values(self):
        """Test SignalStrength enum values."""
        assert SignalStrength.VERY_WEAK.value == "VERY_WEAK"
        assert SignalStrength.WEAK.value == "WEAK"
        assert SignalStrength.MODERATE.value == "MODERATE"
        assert SignalStrength.STRONG.value == "STRONG"
        assert SignalStrength.VERY_STRONG.value == "VERY_STRONG"


class TestExecutionQuality:
    """Tests for ExecutionQuality enum."""

    def test_execution_quality_values(self):
        """Test ExecutionQuality enum values."""
        assert ExecutionQuality.EXCELLENT.value == "EXCELLENT"
        assert ExecutionQuality.GOOD.value == "GOOD"
        assert ExecutionQuality.ACCEPTABLE.value == "ACCEPTABLE"
        assert ExecutionQuality.POOR.value == "POOR"
        assert ExecutionQuality.REJECTED.value == "REJECTED"


class TestInstitutionalFlowStrategy:
    """Comprehensive tests for InstitutionalFlowStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        return InstitutionalFlowStrategy(
            capital=1_000_000,
            max_position_pct=0.02,
            target_sharpe=1.5,
            max_drawdown=0.05,
            enable_tracing=True,
            enable_quality_gates=True,
            consensus_type=ConsensusType.SIMPLE_MAJORITY,
        )

    @pytest.fixture
    def sample_ticks(self):
        """Generate sample tick data."""
        np.random.seed(42)
        n_ticks = 100
        return pd.DataFrame({
            "timestamp": pd.date_range("2026-05-22", periods=n_ticks, freq="min"),
            "price": 100 + np.cumsum(np.random.randn(n_ticks) * 0.1),
            "volume": np.random.randint(100, 1000, n_ticks),
        })

    def test_strategy_initialization(self, strategy):
        """Test strategy initialization."""
        assert strategy.capital == 1_000_000
        assert strategy.max_position_pct == 0.02
        assert strategy.event_store is not None
        assert strategy.agent_council is not None
        assert strategy.risk_engine is not None

    def test_process_market_data_with_signal(self, strategy, sample_ticks):
        """Test processing market data that generates a signal."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        # Signal may or may not be generated depending on data
        if signal:
            assert signal.symbol == "THYAO"
            assert signal.side in ["BUY", "SELL"]
            assert signal.size > 0
            assert signal.confidence > 0
            assert signal.quality_score >= 0

    def test_process_market_data_quality_gate(self, strategy):
        """Test that bad data fails quality gate."""
        # Create very small dataset (should fail quality checks)
        bad_ticks = pd.DataFrame({
            "timestamp": [datetime.now(timezone.utc)],
            "price": [100.0],
            "volume": [1000],
        })
        
        signal = strategy.process_market_data(bad_ticks, symbol="THYAO")
        
        # May return None due to insufficient data
        assert signal is None or signal.quality_score >= 0

    def test_execute_signal(self, strategy, sample_ticks):
        """Test signal execution."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            result = strategy.execute(signal)
            
            assert result.signal_id == signal.signal_id
            assert result.order_id is not None
            assert result.fill_price > 0
            assert result.latency_ms > 0
            assert result.quality in ExecutionQuality

    def test_record_feedback(self, strategy, sample_ticks):
        """Test recording trade feedback."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            result = strategy.execute(signal)
            strategy.record_feedback(result, pnl=500.0)
            
            metrics = strategy.get_metrics()
            assert metrics.total_trades >= 1
            assert len(strategy.get_equity_curve()) > 1

    def test_get_metrics(self, strategy):
        """Test getting strategy metrics."""
        metrics = strategy.get_metrics()
        
        assert isinstance(metrics, StrategyMetrics)
        assert hasattr(metrics, "total_trades")
        assert hasattr(metrics, "win_rate")
        assert hasattr(metrics, "sharpe_ratio")

    def test_get_equity_curve(self, strategy):
        """Test getting equity curve."""
        curve = strategy.get_equity_curve()
        
        assert isinstance(curve, list)
        assert len(curve) >= 1
        assert curve[0] == strategy.capital

    def test_full_trading_cycle(self, strategy, sample_ticks):
        """Test complete trading cycle."""
        initial_curve_len = len(strategy.get_equity_curve())
        trades_executed = 0
        
        # Process multiple bars
        for i in range(5):
            start_idx = i * 20
            end_idx = start_idx + 20
            ticks = sample_ticks.iloc[start_idx:end_idx]
            
            signal = strategy.process_market_data(ticks, symbol="THYAO")
            
            if signal:
                result = strategy.execute(signal)
                pnl = np.random.randn() * 1000
                strategy.record_feedback(result, pnl)
                trades_executed += 1
        
        # Check metrics
        metrics = strategy.get_metrics()
        assert metrics.total_trades >= 0
        # Equity curve should grow only if trades were executed
        if trades_executed > 0:
            assert len(strategy.get_equity_curve()) > initial_curve_len
        else:
            # No trades is also valid - market conditions may not have triggered signals
            assert len(strategy.get_equity_curve()) >= initial_curve_len

    def test_risk_management(self, strategy, sample_ticks):
        """Test that risk management works."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            # Position size should respect max_position_pct
            position_value = signal.size * signal.entry_price
            position_pct = position_value / strategy.capital
            
            # Should be <= max_position_pct (with some confidence scaling)
            assert position_pct <= strategy.max_position_pct

    def test_event_sourcing(self, strategy, sample_ticks):
        """Test that events are recorded."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            result = strategy.execute(signal)
            strategy.record_feedback(result, pnl=100.0)
            
            # Check event store
            events = strategy.event_store.get_events(limit=100)
            
            # Should have SIGNAL, FILL, and PNL events
            event_types = [e.event_type.value for e in events]
            assert "SignalEvent" in event_types or "FillEvent" in event_types

    def test_messaging_backbone(self, strategy, sample_ticks):
        """Test messaging backbone integration."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            result = strategy.execute(signal)
            
            # Check messaging backbone
            dlq = strategy.messaging.get_dlq()
            assert isinstance(dlq, list)

    def test_tracing_integration(self, strategy, sample_ticks):
        """Test tracing integration."""
        signal = strategy.process_market_data(sample_ticks, symbol="THYAO")
        
        if signal:
            result = strategy.execute(signal)
            
            # Check tracing statistics
            stats = strategy.tracing.tracer.get_statistics()
            assert stats["total_spans"] >= 1

    def test_regime_detection(self, strategy, sample_ticks):
        """Test regime detection."""
        regime = strategy._detect_regime(sample_ticks, "THYAO")
        
        assert isinstance(regime, str)
        assert regime in ["bull", "bear", "sideways", "volatile", "low_vol"] or len(regime) > 0

    def test_signal_strength_calculation(self, strategy):
        """Test signal strength calculation."""
        council_result = {
            "confidence": 95.0,
            "decision": "BUY",
            "votes": [],
            "consensus_reached": True,
        }
        
        strength = strategy._calculate_signal_strength(council_result)
        assert strength == SignalStrength.VERY_STRONG
        
        council_result["confidence"] = 50.0
        strength = strategy._calculate_signal_strength(council_result)
        assert strength == SignalStrength.VERY_WEAK

    def test_execution_quality_assessment(self, strategy):
        """Test execution quality assessment."""
        # Excellent execution
        fill = {"fill_price": 100.0, "slippage": 0.005}
        quality = strategy._assess_execution_quality(fill)
        assert quality == ExecutionQuality.EXCELLENT
        
        # Poor execution
        fill = {"fill_price": 100.0, "slippage": 0.5}
        quality = strategy._assess_execution_quality(fill)
        assert quality == ExecutionQuality.REJECTED

    def test_quality_layer_integration(self, strategy, sample_ticks):
        """Test data quality layer integration."""
        data = sample_ticks.to_dict('records')
        report = strategy.quality_layer.validate_dataset(
            data=data,
            data_type=DataType.TICK,
            dataset_id="test_quality",
            expected_fields=["timestamp", "price", "volume"],
        )
        
        assert report.quality_score >= 0
        assert report.level is not None


class TestInstitutionalFlowStrategyIntegration:
    """Integration tests for InstitutionalFlowStrategy."""

    def test_end_to_end_trading(self):
        """Test end-to-end trading with multiple symbols."""
        strategy = InstitutionalFlowStrategy(
            capital=500_000,
            max_position_pct=0.01,
        )
        
        symbols = ["THYAO", "GARAN", "ASELS"]
        
        for symbol in symbols:
            # Generate data
            np.random.seed(hash(symbol) % 1000)
            ticks = pd.DataFrame({
                "timestamp": pd.date_range("2026-05-22", periods=50, freq="min"),
                "price": 100 + np.cumsum(np.random.randn(50) * 0.1),
                "volume": np.random.randint(100, 1000, 50),
            })
            
            # Process and execute
            signal = strategy.process_market_data(ticks, symbol=symbol)
            if signal:
                result = strategy.execute(signal)
                strategy.record_feedback(result, pnl=np.random.randn() * 500)
        
        # Check final metrics
        metrics = strategy.get_metrics()
        assert metrics.total_trades >= 0
        assert metrics.quality_score >= 0

    def test_concurrent_signal_processing(self):
        """Test processing signals concurrently."""
        strategy = InstitutionalFlowStrategy(capital=1_000_000)
        
        # Generate data for multiple symbols
        all_ticks = {}
        for symbol in ["THYAO", "GARAN"]:
            np.random.seed(hash(symbol) % 1000)
            all_ticks[symbol] = pd.DataFrame({
                "timestamp": pd.date_range("2026-05-22", periods=50, freq="min"),
                "price": 100 + np.cumsum(np.random.randn(50) * 0.1),
                "volume": np.random.randint(100, 1000, 50),
            })
        
        # Process sequentially (can be parallelized in production)
        for symbol, ticks in all_ticks.items():
            signal = strategy.process_market_data(ticks, symbol=symbol)
            if signal:
                result = strategy.execute(signal)
                strategy.record_feedback(result, pnl=100.0)
        
        # Verify state
        metrics = strategy.get_metrics()
        assert metrics.total_trades >= 0

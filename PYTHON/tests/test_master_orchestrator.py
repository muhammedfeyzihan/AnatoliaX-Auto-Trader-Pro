"""
PYTHON/tests/test_master_orchestrator.py — Master Orchestrator Testleri

Tests for the master system orchestrator coordinating all 30 features.
"""
import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy.master_orchestrator import (
    MasterOrchestrator,
    OrchestratorConfig,
    SystemState,
    create_master_orchestrator
)


class MockModule:
    """Mock module for testing."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestMasterOrchestrator:
    """Master orchestrator testleri."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Test configuration."""
        return OrchestratorConfig(
            symbols=["THYAO", "GARAN", "AKBNK"],
            base_capital=100000.0,
            max_daily_loss_pct=2.0,
            target_daily_profit_pct=1.0,
            enable_paper_trading=True,
            persistence_path=str(tmp_path / "orchestrator_state.json")
        )
    
    @pytest.fixture
    def orchestrator(self, config):
        """Test orchestrator."""
        return MasterOrchestrator(config=config)
    
    def test_initialization(self, orchestrator):
        """Orchestrator baslatma testi."""
        assert orchestrator.state.status == "initializing"
        assert orchestrator._running == False
        assert len(orchestrator._modules) == 0
    
    def test_register_module(self, orchestrator):
        """Module kaydetme testi."""
        orchestrator.register_module("test_module", MockModule())
        
        assert "test_module" in orchestrator._modules
        assert orchestrator.state.active_features == 1
    
    def test_register_strategy(self, orchestrator):
        """Strateji kaydetme testi."""
        strategy = MockModule()
        orchestrator.register_strategy("optimal_profit", strategy)
        
        assert "optimal_profit" in orchestrator._strategies
    
    def test_event_logging(self, orchestrator):
        """Olay kaydetme testi."""
        orchestrator._log_event("TEST", "Test event", {"data": "value"})
        
        assert len(orchestrator._event_log) == 1
        assert orchestrator._event_log[0]['type'] == "TEST"
        assert orchestrator._event_log[0]['message'] == "Test event"
    
    def test_system_state_update(self, orchestrator):
        """Sistem durumu guncelleme testi."""
        # Add some performance data
        orchestrator._performance_history = [
            {'pnl': 1000, 'timestamp': datetime.now(timezone.utc).isoformat()},
            {'pnl': -500, 'timestamp': datetime.now(timezone.utc).isoformat()}
        ]
        
        orchestrator._update_system_state()
        
        # Should calculate from performance history
        assert orchestrator.state.total_pnl == 500
        assert orchestrator.state.total_trades == 2
        assert orchestrator.state.win_rate == 0.5  # 1 win out of 2
    
    def test_health_score_calculation(self, orchestrator):
        """Saglik skoru hesaplama testi."""
        orchestrator.state.max_drawdown = 0.01
        orchestrator.state.daily_pnl_pct = 0.5
        orchestrator.state.active_features = 15
        orchestrator.state.errors = []
        
        score = orchestrator._calculate_health_score()
        
        assert score > 90  # Should be high with good metrics
    
    def test_health_score_penalty_drawdown(self, orchestrator):
        """Drawdown ceza testi."""
        orchestrator.state.max_drawdown = 0.06  # 6% drawdown
        orchestrator.state.daily_pnl_pct = 0
        orchestrator.state.active_features = 30
        orchestrator.state.errors = []
        
        score = orchestrator._calculate_health_score()
        
        assert score < 90  # Should be penalized
    
    def test_health_score_penalty_errors(self, orchestrator):
        """Hata ceza testi."""
        orchestrator.state.max_drawdown = 0.01
        orchestrator.state.daily_pnl_pct = 0
        orchestrator.state.active_features = 30
        orchestrator.state.errors = ["error1", "error2", "error3"]
        
        score = orchestrator._calculate_health_score()
        
        assert score < 90  # Should be penalized for errors
    
    def test_system_health_check(self, orchestrator):
        """Sistem saglik kontrol testi."""
        # Add required modules
        orchestrator.register_module("risk_engine", MockModule())
        orchestrator.register_module("execution_engine", MockModule())
        orchestrator.register_module("capital_preservation", MockModule())
        
        orchestrator.state.health_score = 80
        orchestrator.state.daily_pnl_pct = 0
        orchestrator.state.max_drawdown = 0.01
        
        healthy = orchestrator._check_system_health()
        
        assert healthy == True
    
    def test_system_health_check_fails_low_score(self, orchestrator):
        """Dusuk saglik skoru testi."""
        orchestrator.state.health_score = 40
        
        healthy = orchestrator._check_system_health()
        
        assert healthy == False
    
    def test_system_health_check_fails_daily_loss(self, orchestrator):
        """Gunluk kayip limiti testi."""
        orchestrator.state.health_score = 80
        orchestrator.state.daily_pnl_pct = -3.0  # Exceeds 2% limit
        
        healthy = orchestrator._check_system_health()
        
        assert healthy == False
    
    def test_full_initialization(self, orchestrator):
        """Tam baslatma testi."""
        # Register all required modules
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule(),
            'agent_council': MockModule(),
            'explainable_ai': MockModule(),
            'cryptographic_audit': MockModule()
        }
        
        for name, module in modules.items():
            orchestrator.register_module(name, module)
        
        # Register optimal strategy
        optimal_strategy = MockModule(
            initialize=lambda modules, knowledge_base: None
        )
        orchestrator.register_strategy("optimal_profit", optimal_strategy)
        
        # Initialize
        orchestrator.initialize()
        
        assert orchestrator.state.status == "initialized"
    
    def test_analyze_symbol_no_health(self, orchestrator):
        """Saglik kontrolunden gecemeyen analiz testi."""
        orchestrator.state.health_score = 30
        
        result = orchestrator.analyze_symbol("THYAO", {'price': 100})
        
        assert result is None
    
    def test_analyze_symbol_with_strategy(self, orchestrator):
        """Strateji ile sembol analizi testi."""
        # Setup health
        orchestrator.state.health_score = 80
        
        # Add required modules
        modules = {
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'capital_preservation': MockModule(should_allow_trade=lambda **k: (True, "OK"))
        }
        for name, module in modules.items():
            orchestrator.register_module(name, module)
        
        # Add optimal strategy that returns a signal
        signal_data = {
            'symbol': 'THYAO',
            'signal': 'BUY',
            'entry_price': 100.0,
            'stop_loss': 95.0,
            'take_profit': 110.0,
            'position_size_pct': 0.1,
            'confidence': 0.75,
            'regime': 'trend_bull',
            'reasoning': {}
        }
        optimal_strategy = MockModule(
            initialize=lambda modules, knowledge_base: None,
            analyze=lambda s, m: MockModule(
                symbol='THYAO',
                direction='LONG',
                entry_price=100.0,
                stop_loss=95.0,
                take_profit=110.0,
                position_size_pct=0.1,
                confidence=0.75,
                regime=MockModule(value='trend_bull'),
                reasoning={}
            ) if s == 'THYAO' else None
        )
        orchestrator.register_strategy("optimal_profit", optimal_strategy)
        
        orchestrator.initialize()
        
        result = orchestrator.analyze_symbol("THYAO", {'price': 100})
        
        assert result is not None
        assert result['symbol'] == "THYAO"
        assert result['signal'] == "BUY"
    
    def test_record_trade(self, orchestrator, tmp_path):
        """Trade kaydetme testi."""
        orchestrator.config.persistence_path = str(tmp_path / "state.json")
        
        # Add optimal strategy
        optimal_strategy = MockModule(
            record_trade_result=lambda s, p, r, f: None
        )
        orchestrator.register_strategy("optimal_profit", optimal_strategy)
        
        orchestrator.record_trade(
            symbol="THYAO",
            pnl=1500.0,
            reasoning="Good trade",
            features={'rsi': 65}
        )
        
        assert len(orchestrator._performance_history) == 1
        assert orchestrator._performance_history[0]['pnl'] == 1500.0
    
    def test_get_status(self, orchestrator):
        """Durum alma testi."""
        orchestrator.state.status = "running"
        orchestrator.state.regime = "trend_bull"
        orchestrator.state.active_features = 30  # Max features for high score
        
        status = orchestrator.get_status()
        
        assert status['status'] == "running"
        assert status['regime'] == "trend_bull"
        assert status['health_score'] >= 90  # Should be high with good config
        assert 'total_pnl' in status
        assert 'sharpe_ratio' in status
    
    def test_get_event_log(self, orchestrator):
        """Olay kayiti alma testi."""
        orchestrator._log_event("EVENT1", "Message 1")
        orchestrator._log_event("EVENT2", "Message 2")
        orchestrator._log_event("EVENT3", "Message 3")
        
        log = orchestrator.get_event_log(limit=2)
        
        assert len(log) == 2
        assert log[0]['type'] == "EVENT2"
        assert log[1]['type'] == "EVENT3"
    
    def test_emergency_stop(self, orchestrator):
        """Acil durum durdurma testi."""
        execution_engine = MockModule(close_all_positions=lambda: None)
        orchestrator.register_module("execution_engine", execution_engine)
        
        orchestrator.emergency_stop()
        
        assert orchestrator.state.status == "emergency_stopped"
        assert "Emergency stop triggered" in orchestrator.state.errors
    
    def test_factory_function(self):
        """Factory function testi."""
        orchestrator = create_master_orchestrator()
        assert isinstance(orchestrator, MasterOrchestrator)
    
    @pytest.mark.asyncio
    async def test_start_stop(self, orchestrator):
        """Baslatma ve durdurma testi."""
        # Add required modules
        modules = {
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'capital_preservation': MockModule(check=lambda: {'allowed': True})
        }
        for name, module in modules.items():
            orchestrator.register_module(name, module)
        
        await orchestrator.start()
        
        assert orchestrator._running == True
        assert orchestrator.state.status == "running"
        assert len(orchestrator._tasks) > 0
        
        await orchestrator.stop()
        
        assert orchestrator._running == False
        assert orchestrator.state.status == "stopped"
    
    @pytest.mark.asyncio
    async def test_background_loops(self, orchestrator, tmp_path):
        """Arka plan dongu testi."""
        orchestrator.config.persistence_path = str(tmp_path / "state.json")
        orchestrator.config.data_refresh_interval_sec = 1
        orchestrator.config.risk_check_interval_sec = 1
        orchestrator.config.learning_interval_sec = 1
        
        # Add modules
        modules = {
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'capital_preservation': MockModule(check=lambda: {'allowed': True}),
            'meta_learner': MockModule(periodic_update=lambda x: None),
            'self_healing': MockModule(check_and_repair=lambda: [])
        }
        for name, module in modules.items():
            orchestrator.register_module(name, module)
        
        await orchestrator.start()
        
        # Let loops run for a bit
        await asyncio.sleep(2)
        
        await orchestrator.stop()
        
        # Should have logged events
        assert len(orchestrator._event_log) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


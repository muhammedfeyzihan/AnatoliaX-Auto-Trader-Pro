"""
PYTHON/tests/test_optimal_profit_strategy.py — Optimal Profit Strategy Testleri

Tests for the optimal profit master strategy combining all 30 features.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy.optimal_profit_strategy import (
    OptimalProfitStrategy,
    StrategyConfig,
    StrategyMode,
    MarketRegime,
    create_optimal_strategy
)


class MockModule:
    """Mock module for testing."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestOptimalProfitStrategy:
    """Optimal profit strategy testleri."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return StrategyConfig(
            mode=StrategyMode.BALANCED,
            max_daily_loss_pct=2.0,
            target_daily_profit_pct=1.0
        )
    
    @pytest.fixture
    def strategy(self, config):
        """Test strategy."""
        return OptimalProfitStrategy(config=config)
    
    def test_initialization(self, strategy):
        """Strateji baslatma testi."""
        assert strategy.config.mode == StrategyMode.BALANCED
        assert strategy._initialized == False
        assert len(strategy._active_trades) == 0
    
    def test_initialize_with_modules(self, strategy):
        """Modul entegrasyon testi."""
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        
        strategy.initialize(modules=modules)
        
        assert strategy._initialized == True
        assert len(strategy._modules) == 9
    
    def test_regime_detection(self, strategy):
        """Rejim tespiti testi."""
        modules = {
            'regime_detector': MockModule(detect=lambda x: 'high_volatility'),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        market_data = {'volatility': 0.04, 'trend_strength': 0.3}
        regime = strategy._detect_regime(market_data)
        
        assert regime == MarketRegime.HIGH_VOLATILITY
    
    def test_strategy_mode_selection(self, strategy):
        """Strateji modu secimi testi."""
        # Crisis -> Preservation
        mode = strategy._select_strategy_mode(MarketRegime.CRISIS)
        assert mode == StrategyMode.PRESERVATION
        
        # Trend -> Aggressive
        mode = strategy._select_strategy_mode(MarketRegime.TREND_BULL)
        assert mode == StrategyMode.AGGRESSIVE
        
        # Range -> Balanced
        mode = strategy._select_strategy_mode(MarketRegime.RANGE)
        assert mode == StrategyMode.BALANCED
    
    def test_position_sizing(self, strategy):
        """Pozisyon boyutu testi."""
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        signal = {'win_rate': 0.6, 'reward_ratio': 1.5}
        
        # Test different modes
        strategy._mode = StrategyMode.AGGRESSIVE
        size_agg = strategy._calculate_position_size(signal, MarketRegime.TREND_BULL)
        
        strategy._mode = StrategyMode.PRESERVATION
        size_pres = strategy._calculate_position_size(signal, MarketRegime.CRISIS)
        
        # Aggressive should be larger than preservation
        assert size_agg > size_pres
    
    def test_signal_generation(self, strategy):
        """Sinyal uretme testi."""
        agent_council = MockModule(
            get_consensus=lambda s, c: {
                'approved': True,
                'direction': 'LONG',
                'confidence': 0.75,
                'votes': {'signal': 1, 'risk': 1, 'strategy': 1},
                'features': {'rsi': 65, 'macd': 'bullish'}
            }
        )
        
        modules = {
            'regime_detector': MockModule(detect=lambda x: 'trend_bull'),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(check_liquidity=lambda s: True),
            'macro_intelligence': MockModule(is_safe_to_trade=lambda: True),
            'capital_preservation': MockModule(should_allow_trade=lambda **k: (True, "OK")),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule(),
            'agent_council': agent_council
        }
        strategy.initialize(modules=modules)
        
        market_data = {
            'price': 100.0,
            'volatility': 0.02,
            'trend_strength': 0.8,
            'trend_direction': 1
        }
        
        signal = strategy.analyze("THYAO", market_data)
        
        assert signal is not None
        assert signal.symbol == "THYAO"
        assert signal.direction == "LONG"
        assert signal.confidence == 0.75
        assert signal.entry_price == 100.0
    
    def test_no_signal_on_macro_event(self, strategy):
        """Makro olayda sinyal engelleme testi."""
        macro_intel = MockModule(is_safe_to_trade=lambda: False)
        
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': macro_intel,
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        market_data = {'price': 100.0}
        signal = strategy.analyze("THYAO", market_data)
        
        assert signal is None
    
    def test_trade_result_recording(self, strategy):
        """Trade sonucu kaydetme testi."""
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(update=lambda x: None),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        strategy.record_trade_result(
            symbol="THYAO",
            pnl=1500.0,
            reasoning="Good entry on breakout",
            features={'rsi': 65}
        )
        
        assert len(strategy._performance_history) == 1
        assert strategy._performance_history[0]['pnl'] == 1500.0
    
    def test_performance_stats(self, strategy):
        """Performans istatistikleri testi."""
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        # Add some trades
        strategy.record_trade_result("THYAO", 1000.0, "Test", {})
        strategy.record_trade_result("GARAN", -500.0, "Test", {})
        strategy.record_trade_result("AKBNK", 800.0, "Test", {})
        
        stats = strategy.get_performance_stats()
        
        assert stats['total_trades'] == 3
        assert stats['total_pnl'] == 1300.0
        assert stats['win_rate'] == 2/3  # 2 wins out of 3
    
    def test_exit_signal(self, strategy):
        """Cikis sinyali testi."""
        modules = {
            'regime_detector': MockModule(),
            'meta_learner': MockModule(),
            'risk_engine': MockModule(),
            'execution_engine': MockModule(),
            'liquidity_intelligence': MockModule(),
            'macro_intelligence': MockModule(),
            'capital_preservation': MockModule(),
            'position_sizing': MockModule(),
            'portfolio_optimizer': MockModule()
        }
        strategy.initialize(modules=modules)
        
        # Add a trade
        market_data = {'price': 100.0, 'volatility': 0.02}
        signal = strategy.analyze("THYAO", market_data)
        
        # Test stop loss
        exit_type = strategy.should_exit_trade("THYAO", 95.0)
        assert exit_type in ['STOP_LOSS', 'TAKE_PROFIT', None]
    
    def test_factory_function(self):
        """Factory function testi."""
        strategy = create_optimal_strategy()
        assert isinstance(strategy, OptimalProfitStrategy)
    
    def test_explainable_ai(self, strategy):
        """Explainable AI testi."""
        xai_module = MockModule(
            explain=lambda s: {
                'symbol': s.symbol,
                'confidence': s.confidence,
                'reasoning': 'AI explanation'
            }
        )
        
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
            'explainable_ai': xai_module
        }
        strategy.initialize(modules=modules)
        
        market_data = {'price': 100.0, 'volatility': 0.02}
        signal = strategy.analyze("THYAO", market_data)
        
        if signal:
            explanation = strategy.get_explanation(signal)
            assert 'symbol' in explanation
            assert 'confidence' in explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


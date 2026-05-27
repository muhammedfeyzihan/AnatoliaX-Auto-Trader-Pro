"""
PYTHON/tests/test_missing_components.py — Tests for All Missing Critical Components

Tests for:
- Market Data Normalizer
- Config Manager
- Backup & Disaster Recovery
- Survival Strategy (Layer 4)
"""
import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMarketDataNormalizer:
    """Market Data Normalizer tests."""
    
    def test_normalizer_creation(self):
        from data.market_data_normalizer import MarketDataNormalizer
        normalizer = MarketDataNormalizer()
        assert normalizer is not None
    
    def test_bist_tick_normalization(self):
        from data.market_data_normalizer import MarketDataNormalizer
        normalizer = MarketDataNormalizer()
        
        raw_tick = {
            'symbol': 'THYAO',
            'price': 100.5,
            'volume': 1000,
            'bid': 100.4,
            'ask': 100.6,
            'bid_size': 500,
            'ask_size': 500,
            'trade_id': '12345'
        }
        
        tick = normalizer.normalize_tick('BIST', raw_tick)
        
        assert tick is not None
        assert tick.symbol == 'THYAO'
        assert tick.price == 100.5
        assert tick.exchange == 'BIST'
    
    def test_invalid_data_rejection(self):
        from data.market_data_normalizer import MarketDataNormalizer
        normalizer = MarketDataNormalizer()
        
        # Missing required fields
        raw_tick = {'symbol': 'THYAO'}
        
        tick = normalizer.normalize_tick('BIST', raw_tick)
        
        assert tick is None
    
    def test_quality_report(self):
        from data.market_data_normalizer import MarketDataNormalizer
        normalizer = MarketDataNormalizer()
        
        # Generate some quality issues
        normalizer.normalize_tick('BIST', {'symbol': 'THYAO'})
        normalizer.normalize_tick('UNKNOWN', {'price': 100})
        
        report = normalizer.get_quality_report()
        
        assert 'total_issues' in report
        assert 'by_exchange' in report
        assert 'by_type' in report


class TestConfigManager:
    """Configuration Manager tests."""
    
    def test_config_manager_creation(self):
        from common.config_manager import ConfigManager
        manager = ConfigManager()
        assert manager is not None
    
    def test_trading_config(self):
        from common.config_manager import ConfigManager
        manager = ConfigManager()
        
        config = manager.get_trading_config()
        
        assert config.max_position_size_pct == 10.0
        assert config.max_daily_loss_pct == 2.0
        assert config.enable_paper_trading == True
    
    def test_feature_flags(self):
        from common.config_manager import ConfigManager, FeatureFlagState
        manager = ConfigManager()
        
        flags = manager.get_feature_flags()
        
        assert 'gpu_acceleration' in flags
        assert 'auto_deleveraging' in flags
        assert 'alpha_decay_detection' in flags
    
    def test_enable_disable_feature(self):
        from common.config_manager import ConfigManager, FeatureFlagState
        manager = ConfigManager()
        
        # Disable feature
        success = manager.disable_feature('gpu_acceleration')
        assert success == True
        assert manager.is_feature_enabled('gpu_acceleration') == False
        
        # Enable feature
        success = manager.enable_feature('gpu_acceleration', FeatureFlagState.ENABLED)
        assert success == True
        assert manager.is_feature_enabled('gpu_acceleration') == True


class TestBackupRecovery:
    """Backup & Disaster Recovery tests."""
    
    def test_dr_system_creation(self):
        from infrastructure.backup_recovery import DisasterRecoverySystem
        dr = DisasterRecoverySystem()
        assert dr is not None
    
    def test_create_snapshot(self, tmp_path):
        from infrastructure.backup_recovery import DisasterRecoverySystem, BackupTier, LocalStorage
        storage = LocalStorage(base_path=str(tmp_path / "backups"))
        dr = DisasterRecoverySystem(storage=storage)
        
        state_data = {'positions': [{'symbol': 'THYAO', 'size': 100}]}
        
        snapshot = dr.create_snapshot('positions', state_data, tier=BackupTier.LOCAL)
        
        assert snapshot is not None
        assert snapshot.snapshot_id is not None
        assert snapshot.state_type == 'positions'
        assert snapshot.checksum is not None
    
    def test_recovery_plans(self):
        from infrastructure.backup_recovery import DisasterRecoverySystem
        dr = DisasterRecoverySystem()
        
        plans = dr.get_all_recovery_plans()
        
        assert 'node_failure' in plans
        assert 'database_failure' in plans
        assert 'datacenter_failure' in plans
        assert 'region_failure' in plans
        assert 'complete_catastrophe' in plans
    
    def test_rpo_rto(self):
        from infrastructure.backup_recovery import DisasterRecoverySystem
        dr = DisasterRecoverySystem()
        
        # RPO for critical data should be 0
        rpo_positions = dr.get_recovery_point_objective('positions')
        assert rpo_positions == 0
        
        # RTO for node failure should be 1 minute
        rto_node = dr.get_recovery_time_objective('node_failure')
        assert rto_node == 1
    
    def test_backup_stats(self, tmp_path):
        from infrastructure.backup_recovery import DisasterRecoverySystem, BackupTier, LocalStorage
        storage = LocalStorage(base_path=str(tmp_path / "backups"))
        dr = DisasterRecoverySystem(storage=storage)
        
        # Create some snapshots
        dr.create_snapshot('positions', {'data': 1})
        dr.create_snapshot('orders', {'data': 2})
        
        stats = dr.get_backup_stats()
        
        assert 'total_snapshots' in stats
        assert stats['total_snapshots'] >= 2
        assert 'total_size_bytes' in stats


class TestSurvivalStrategy:
    """Layer 4 Survival Strategy tests."""
    
    def test_survival_strategy_creation(self):
        from strategy.survival_strategy import SurvivalStrategy
        strategy = SurvivalStrategy('test_strategy')
        assert strategy is not None
    
    def test_consecutive_losses(self):
        from strategy.survival_strategy import SurvivalStrategy
        strategy = SurvivalStrategy('test_strategy')
        
        # Ingest 5 consecutive losses
        for i in range(5):
            strategy.ingest_trade(pnl=-100.0, regime='trend')
        
        metrics = strategy._calculate_metrics()
        
        assert metrics.max_consecutive_losses == 5
    
    def test_adaptation_action(self):
        from strategy.survival_strategy import SurvivalStrategy, AdaptationAction, StrategyHealthStatus
        strategy = SurvivalStrategy('test_strategy')
        
        # Healthy strategy should continue
        action = strategy.get_adaptation_action()
        assert action == AdaptationAction.CONTINUE
        
        # Force critical status
        strategy._health_status = StrategyHealthStatus.CRITICAL
        action = strategy.get_adaptation_action()
        assert action == AdaptationAction.EVOLVE
    
    def test_strategy_status(self):
        from strategy.survival_strategy import SurvivalStrategy
        strategy = SurvivalStrategy('test_strategy')
        
        # Add some trades
        for i in range(10):
            strategy.ingest_trade(pnl=100.0, regime='trend')
        
        status = strategy.get_status()
        
        assert 'strategy_id' in status
        assert 'health_status' in status
        assert 'lifetime_trades' in status
        assert 'total_pnl' in status
        assert status['lifetime_trades'] == 10
    
    def test_regime_mismatch(self):
        from strategy.survival_strategy import SurvivalStrategy
        strategy = SurvivalStrategy('test_strategy')
        
        # Add trades with consistent regime
        for i in range(20):
            strategy.ingest_trade(pnl=100.0, regime='trend')
        
        # Check mismatch with different regime
        mismatch = strategy.check_regime_mismatch('range')
        
        assert mismatch is not None
        assert mismatch.detected == True
        assert mismatch.expected_regime == 'trend'
        assert mismatch.actual_regime == 'range'
    
    def test_strategy_evolution(self):
        from strategy.survival_strategy import SurvivalStrategy
        strategy = SurvivalStrategy('test_strategy')
        
        performance_data = {
            'win_rate': 0.4,
            'profit_factor': 1.2,
            'sharpe': 0.5,
            'max_drawdown': 0.15
        }
        
        evolution = strategy.evolve_strategy(performance_data)
        
        assert evolution is not None
        assert evolution.parent_strategy_id == 'test_strategy'
        assert evolution.evolved_strategy_id.startswith('test_strategy_gen')


class TestIntegration:
    """Integration tests for critical components."""
    
    def test_config_with_survival_strategy(self):
        from common.config_manager import ConfigManager
        from strategy.survival_strategy import SurvivalStrategy
        
        manager = ConfigManager()
        strategy = SurvivalStrategy('test')
        
        # Get thresholds from config
        risk_config = manager.get_risk_config()
        
        # Use config in strategy
        strategy.thresholds['max_drawdown'] = risk_config.kill_switch_drawdown_pct
        
        assert strategy.thresholds['max_drawdown'] > 0
    
    def test_normalizer_with_config(self):
        from data.market_data_normalizer import MarketDataNormalizer
        from common.config_manager import ConfigManager
        
        normalizer = MarketDataNormalizer()
        manager = ConfigManager()
        
        # Enable multi-exchange feature
        manager.enable_feature('multi_exchange')
        
        # Add exchange
        from data.market_data_normalizer import BISTAdapter
        normalizer.register_adapter('BIST', BISTAdapter())
        
        # Check feature is enabled
        assert manager.is_feature_enabled('multi_exchange') == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


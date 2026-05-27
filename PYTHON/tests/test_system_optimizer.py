"""
PYTHON/tests/test_system_optimizer.py — System Optimizer Testleri

Tests for comprehensive system optimization configuration.
"""
import pytest
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from optimization.system_optimizer import (
    SystemOptimizer,
    OptimizationPreset,
    HardwareTier,
    OptimizationConfig,
    get_system_optimizer,
    apply_optimization_preset,
    optimize_for_production,
    optimize_for_backtesting
)


class TestOptimizationPreset:
    """Optimization preset testleri."""
    
    def test_preset_enum_values(self):
        """Preset enum degerleri testi."""
        assert OptimizationPreset.DEVELOPMENT.value == "development"
        assert OptimizationPreset.BACKTESTING.value == "backtesting"
        assert OptimizationPreset.PRODUCTION.value == "production"
        assert OptimizationPreset.HFT.value == "hft"
        assert OptimizationPreset.CONSERVATIVE.value == "conservative"


class TestHardwareTier:
    """Hardware tier testleri."""
    
    def test_tier_enum_values(self):
        """Tier enum degerleri testi."""
        assert HardwareTier.ENTRY.value == "entry"
        assert HardwareTier.MID.value == "mid"
        assert HardwareTier.HIGH.value == "high"
        assert HardwareTier.EXTREME.value == "extreme"
        assert HardwareTier.INSTITUTIONAL.value == "institutional"


class TestSystemOptimizer:
    """System optimizer testleri."""
    
    @pytest.fixture
    def optimizer(self):
        """Test optimizer."""
        return SystemOptimizer()
    
    def test_initialization(self, optimizer):
        """Optimizer baslatma testi."""
        assert optimizer.config is not None
        assert optimizer.hardware is not None
        assert optimizer.hardware.cpu_count > 0
        assert optimizer.hardware.total_memory_gb > 0
    
    def test_hardware_detection(self, optimizer):
        """Hardware tespiti testi."""
        hw = optimizer.hardware
        
        assert hw.cpu_count >= 1
        assert hw.cpu_physical_cores >= 1
        assert hw.cpu_logical_cores >= 1
        assert hw.total_memory_gb > 0
        assert hw.tier in HardwareTier
    
    def test_tier_determination(self, optimizer):
        """Tier belirleme testi."""
        tier = optimizer.hardware.tier
        
        # Tier should match hardware capabilities
        if optimizer.hardware.cpu_physical_cores >= 32:
            assert tier in [HardwareTier.EXTREME, HardwareTier.INSTITUTIONAL]
        elif optimizer.hardware.cpu_physical_cores >= 16:
            assert tier in [HardwareTier.HIGH, HardwareTier.EXTREME, HardwareTier.INSTITUTIONAL]
        elif optimizer.hardware.cpu_physical_cores >= 8:
            assert tier in [HardwareTier.MID, HardwareTier.HIGH, HardwareTier.EXTREME, HardwareTier.INSTITUTIONAL]
    
    def test_auto_configure(self):
        """Auto-configuration testi."""
        optimizer = SystemOptimizer.auto_configure()
        
        assert optimizer._applied_preset == OptimizationPreset.DEVELOPMENT
        assert optimizer.config.num_workers > 0
        assert optimizer.config.thread_pool_size > 0
    
    def test_apply_development_preset(self, optimizer):
        """Development preset uygulama testi."""
        optimizer.apply_preset(OptimizationPreset.DEVELOPMENT)
        
        assert optimizer.config.log_level == "DEBUG"
        assert optimizer.config.process_priority == "normal"
        assert optimizer._applied_preset == OptimizationPreset.DEVELOPMENT
    
    def test_apply_backtesting_preset(self, optimizer):
        """Backtesting preset uygulama testi."""
        optimizer.apply_preset(OptimizationPreset.BACKTESTING)
        
        assert optimizer.config.parallel_backtest == True
        assert optimizer.config.vectorized_computation == True
        assert optimizer.config.numba_acceleration == True
        assert optimizer._applied_preset == OptimizationPreset.BACKTESTING
    
    def test_apply_production_preset(self, optimizer):
        """Production preset uygulama testi."""
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        assert optimizer.config.parallel_backtest == True
        assert optimizer.config.metrics_enabled == True
        assert optimizer.config.tracing_enabled == True
        assert optimizer.config.process_priority == "high"
        assert optimizer._applied_preset == OptimizationPreset.PRODUCTION
    
    def test_apply_hft_preset(self, optimizer):
        """HFT preset uygulama testi."""
        optimizer.apply_preset(OptimizationPreset.HFT)
        
        assert optimizer.config.parallel_backtest == False
        assert optimizer.config.risk_check_interval_ms == 10
        assert optimizer.config.order_batch_size == 1
        assert optimizer.config.io_batch_size == 1
        assert optimizer.config.process_priority == "realtime"
        assert optimizer._applied_preset == OptimizationPreset.HFT
    
    def test_apply_conservative_preset(self, optimizer):
        """Conservative preset uygulama testi."""
        optimizer.apply_preset(OptimizationPreset.CONSERVATIVE)
        
        assert optimizer.config.num_workers <= 2
        assert optimizer.config.max_memory_mb <= 2048
        assert optimizer.config.max_concurrent_positions <= 3
        assert optimizer.config.process_priority == "low"
        assert optimizer._applied_preset == OptimizationPreset.CONSERVATIVE
    
    def test_get_optimized_config(self, optimizer):
        """Optimize edilmis config alma testi."""
        config = optimizer.get_optimized_config()
        
        assert isinstance(config, OptimizationConfig)
        assert config.num_workers > 0
        assert config.max_memory_mb > 0
    
    def test_get_hardware_info(self, optimizer):
        """Hardware bilgisi alma testi."""
        hw = optimizer.get_hardware_info()
        
        assert hw.cpu_count > 0
        assert hw.total_memory_gb > 0
        assert hw.tier in HardwareTier
    
    def test_get_optimization_report(self, optimizer):
        """Optimizasyon raporu testi."""
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        report = optimizer.get_optimization_report()
        
        assert 'hardware' in report
        assert 'optimization' in report
        assert 'history' in report
        
        assert report['hardware']['cpu_physical_cores'] > 0
        assert report['hardware']['memory_gb'] > 0
        assert report['optimization']['preset'] == 'production'
    
    def test_optimization_history(self, optimizer):
        """Optimizasyon gecmisi testi."""
        optimizer.apply_preset(OptimizationPreset.DEVELOPMENT)
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        optimizer.apply_preset(OptimizationPreset.HFT)
        
        assert len(optimizer._optimization_history) == 3
        assert optimizer._optimization_history[0]['action'] == 'apply_preset_development'
        assert optimizer._optimization_history[1]['action'] == 'apply_preset_production'
        assert optimizer._optimization_history[2]['action'] == 'apply_preset_hft'
    
    def test_save_and_load_config(self, optimizer, tmp_path):
        """Config kaydetme ve yukleme testi."""
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        config_path = tmp_path / "optimizer_config.json"
        optimizer.save_config(str(config_path))
        
        assert config_path.exists()
        
        # Load config
        loaded_optimizer = SystemOptimizer.load_config(str(config_path))
        
        assert loaded_optimizer.config.num_workers == optimizer.config.num_workers
        assert loaded_optimizer.config.max_memory_mb == optimizer.config.max_memory_mb
        assert loaded_optimizer._applied_preset == OptimizationPreset.PRODUCTION
    
    def test_global_optimizer_singleton(self):
        """Global optimizer singleton testi."""
        optimizer1 = get_system_optimizer()
        optimizer2 = get_system_optimizer()
        
        assert optimizer1 is optimizer2
    
    def test_convenience_functions(self):
        """Kolaylik fonksiyonlari testi."""
        # Production
        prod_optimizer = optimize_for_production()
        assert prod_optimizer._applied_preset == OptimizationPreset.PRODUCTION
        
        # Backtesting
        backtest_optimizer = optimize_for_backtesting()
        assert backtest_optimizer._applied_preset == OptimizationPreset.BACKTESTING
    
    def test_apply_preset_function(self):
        """Apply preset fonksiyon testi."""
        optimizer = apply_optimization_preset('hft')
        assert optimizer._applied_preset == OptimizationPreset.HFT
    
    def test_config_defaults(self, optimizer):
        """Config varsayilan degerleri testi."""
        config = optimizer.config
        
        assert config.async_io_enabled == True
        assert config.disk_cache_enabled == True
        assert config.compression_enabled == True
        assert config.metrics_enabled == True
        assert config.model_cache_enabled == True
    
    def test_memory_configuration(self, optimizer):
        """Memory yapilandirmasi testi."""
        optimizer.apply_preset(OptimizationPreset.BACKTESTING)
        
        # Backtesting should use more memory
        assert optimizer.config.max_memory_mb > 2048
        assert optimizer.config.cache_size_mb > 256
    
    def test_threading_configuration(self, optimizer):
        """Threading yapilandirmasi testi."""
        config = optimizer.config
        
        assert config.num_workers >= 1
        assert config.thread_pool_size >= 1
        assert config.num_workers <= optimizer.hardware.cpu_physical_cores
    
    def test_gpu_configuration(self, optimizer):
        """GPU yapilandirmasi testi."""
        # GPU acceleration should match hardware capability
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        if optimizer.hardware.gpu_available:
            assert optimizer.config.gpu_acceleration == True
            assert optimizer.config.gpu_inference == True
        else:
            assert optimizer.config.gpu_acceleration == False
    
    def test_risk_configuration(self, optimizer):
        """Risk yapilandirmasi testi."""
        optimizer.apply_preset(OptimizationPreset.HFT)
        
        # HFT should have fastest risk checks
        assert optimizer.config.risk_check_interval_ms == 10
        
        optimizer.apply_preset(OptimizationPreset.CONSERVATIVE)
        
        # Conservative should have slower risk checks
        assert optimizer.config.risk_check_interval_ms == 200
    
    def test_logging_configuration(self, optimizer):
        """Logging yapilandirmasi testi."""
        optimizer.apply_preset(OptimizationPreset.DEVELOPMENT)
        assert optimizer.config.log_level == "DEBUG"
        
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        assert optimizer.config.log_level == "WARNING"
        
        optimizer.apply_preset(OptimizationPreset.HFT)
        assert optimizer.config.log_level == "ERROR"
    
    def test_print_report(self, optimizer, capsys):
        """Report yazdirma testi."""
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        optimizer.print_report()
        
        captured = capsys.readouterr()
        
        assert "ANATOLIAX" in captured.out
        assert "HARDWARE" in captured.out
        assert "CPU" in captured.out
    
    def test_optimizer_with_knowledge_base(self, optimizer):
        """Optimizer + knowledge base entegrasyon testi."""
        from agents.knowledge_base import KnowledgeBase
        
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        # Knowledge base should work with optimized settings
        kb = KnowledgeBase()
        
        assert kb is not None
        assert optimizer.config.model_cache_enabled == True
    
    def test_optimizer_with_strategy(self, optimizer):
        """Optimizer + strategy entegrasyon testi."""
        from strategy.optimal_profit_strategy import OptimalProfitStrategy, StrategyConfig
        
        optimizer.apply_preset(OptimizationPreset.BACKTESTING)
        
        # Strategy should work with optimized settings
        config = StrategyConfig()
        strategy = OptimalProfitStrategy(config=config)
        
        assert strategy is not None
        assert optimizer.config.parallel_backtest == True
    
    def test_optimizer_with_orchestrator(self, optimizer):
        """Optimizer + orchestrator entegrasyon testi."""
        from strategy.master_orchestrator import MasterOrchestrator, OrchestratorConfig
        
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        # Orchestrator should work with optimized settings
        config = OrchestratorConfig()
        orchestrator = MasterOrchestrator(config=config)
        
        assert orchestrator is not None
        assert optimizer.config.metrics_enabled == True


class TestOptimizationIntegration:
    """Optimizasyon entegrasyon testleri."""
    
    def test_optimizer_with_knowledge_base(self):
        """Optimizer + knowledge base entegrasyon testi."""
        from agents.knowledge_base import KnowledgeBase
        
        optimizer = SystemOptimizer.auto_configure()
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        # Knowledge base should work with optimized settings
        kb = KnowledgeBase()
        
        assert kb is not None
        assert optimizer.config.model_cache_enabled == True
    
    def test_optimizer_with_strategy(self):
        """Optimizer + strategy entegrasyon testi."""
        from strategy.optimal_profit_strategy import OptimalProfitStrategy, StrategyConfig
        
        optimizer = SystemOptimizer.auto_configure()
        optimizer.apply_preset(OptimizationPreset.BACKTESTING)
        
        # Strategy should work with optimized settings
        config = StrategyConfig()
        strategy = OptimalProfitStrategy(config=config)
        
        assert strategy is not None
        assert optimizer.config.parallel_backtest == True
    
    def test_optimizer_with_orchestrator(self):
        """Optimizer + orchestrator entegrasyon testi."""
        from strategy.master_orchestrator import MasterOrchestrator, OrchestratorConfig
        
        optimizer = SystemOptimizer.auto_configure()
        optimizer.apply_preset(OptimizationPreset.PRODUCTION)
        
        # Orchestrator should work with optimized settings
        config = OrchestratorConfig()
        orchestrator = MasterOrchestrator(config=config)
        
        assert orchestrator is not None
        assert optimizer.config.metrics_enabled == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


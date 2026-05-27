"""
PYTHON/optimization/system_optimizer.py — Comprehensive System Optimization

Centralized optimization configuration and management for all 30 features.

This module provides:
- Global optimization settings
- Performance tuning presets
- Hardware-aware configuration
- Auto-optimization based on system resources
- Integration with all 30 institutional features

Usage:
    from optimization.system_optimizer import SystemOptimizer, OptimizationPreset
    
    # Auto-detect and apply optimal settings
    optimizer = SystemOptimizer.auto_configure()
    optimizer.apply_preset(OptimizationPreset.PRODUCTION)
    
    # Get optimized settings
    config = optimizer.get_optimized_config()
"""
import os
import sys
import json
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import numpy as np


class OptimizationPreset(Enum):
    """Optimization presets for different use cases."""
    DEVELOPMENT = "development"      # Debug-friendly, slower
    BACKTESTING = "backtesting"      # Optimized for backtesting
    PAPER_TRADING = "paper_trading"  # Real-time simulation
    PRODUCTION = "production"        # Maximum performance
    HFT = "hft"                      # Ultra-low latency
    CONSERVATIVE = "conservative"    # Safe, resource-limited


class HardwareTier(Enum):
    """Hardware capability tiers."""
    ENTRY = "entry"           # 4 cores, 8GB RAM
    MID = "mid"              # 8 cores, 16GB RAM
    HIGH = "high"            # 16 cores, 32GB RAM
    EXTREME = "extreme"      # 32+ cores, 64GB+ RAM
    INSTITUTIONAL = "institutional"  # Dedicated trading hardware


@dataclass
class OptimizationConfig:
    """Complete optimization configuration."""
    # CPU/Threading
    num_workers: int = 4
    cpu_affinity: List[int] = field(default_factory=list)
    thread_pool_size: int = 4
    process_priority: str = "normal"  # low, normal, high, realtime
    
    # Memory
    max_memory_mb: int = 4096
    cache_size_mb: int = 512
    enable_memory_pooling: bool = True
    garbage_collection_interval: int = 300  # seconds
    
    # I/O
    io_batch_size: int = 1000
    async_io_enabled: bool = True
    disk_cache_enabled: bool = True
    compression_enabled: bool = True
    
    # Network
    connection_pool_size: int = 10
    request_timeout_sec: float = 5.0
    retry_attempts: int = 3
    websocket_buffer_size: int = 65536
    
    # Backtest
    parallel_backtest: bool = True
    vectorized_computation: bool = True
    numba_acceleration: bool = True
    gpu_acceleration: bool = False
    
    # Trading
    order_batch_size: int = 10
    risk_check_interval_ms: int = 100
    market_data_buffer_size: int = 10000
    tick_buffer_size: int = 1000
    
    # Logging/Observability
    log_level: str = "INFO"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    sampling_rate: float = 0.1  # 10% sampling for traces
    
    # AI/ML
    model_cache_enabled: bool = True
    inference_batch_size: int = 32
    gpu_inference: bool = False
    model_quantization: bool = True
    
    # Risk
    max_concurrent_positions: int = 10
    position_check_interval_ms: int = 50
    risk_calculation_method: str = "var"  # var, cvar, expected_shortfall
    
    # Database
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_timeout_sec: int = 30
    db_echo: bool = False


@dataclass
class HardwareInfo:
    """System hardware information."""
    cpu_count: int = 0
    cpu_physical_cores: int = 0
    cpu_logical_cores: int = 0
    cpu_frequency_ghz: float = 0.0
    total_memory_gb: float = 0.0
    available_memory_gb: float = 0.0
    gpu_available: bool = False
    gpu_count: int = 0
    gpu_memory_gb: float = 0.0
    disk_type: str = "unknown"  # ssd, hdd, nvme
    network_speed_mbps: float = 0.0
    tier: HardwareTier = HardwareTier.ENTRY


class SystemOptimizer:
    """
    Comprehensive System Optimizer.
    
    Manages all optimization settings for the AnatoliaX system.
    Auto-detects hardware and applies optimal configurations.
    """
    
    def __init__(self):
        self.config = OptimizationConfig()
        self.hardware = HardwareInfo()
        self._applied_preset: Optional[OptimizationPreset] = None
        self._optimization_history: List[Dict] = []
        
        self._detect_hardware()
    
    @classmethod
    def auto_configure(cls) -> 'SystemOptimizer':
        """Auto-detect hardware and configure optimal settings."""
        optimizer = cls()
        optimizer._auto_configure()
        return optimizer
    
    def _detect_hardware(self) -> None:
        """Detect system hardware capabilities."""
        # CPU
        self.hardware.cpu_count = psutil.cpu_count(logical=True) or 1
        self.hardware.cpu_physical_cores = psutil.cpu_count(logical=False) or 1
        self.hardware.cpu_logical_cores = self.hardware.cpu_count
        
        try:
            freq = psutil.cpu_freq()
            self.hardware.cpu_frequency_ghz = (freq.current or 0) / 1000.0
        except Exception:
            self.hardware.cpu_frequency_ghz = 0.0
        
        # Memory
        mem = psutil.virtual_memory()
        self.hardware.total_memory_gb = mem.total / (1024 ** 3)
        self.hardware.available_memory_gb = mem.available / (1024 ** 3)
        
        # GPU (basic detection)
        try:
            import torch
            self.hardware.gpu_available = torch.cuda.is_available()
            if self.hardware.gpu_available:
                self.hardware.gpu_count = torch.cuda.device_count()
                self.hardware.gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        except ImportError:
            self.hardware.gpu_available = False
        
        # Determine tier
        self.hardware.tier = self._determine_tier()
        
        # Disk type (basic detection)
        self.hardware.disk_type = self._detect_disk_type()
    
    def _determine_tier(self) -> HardwareTier:
        """Determine hardware tier based on capabilities."""
        cores = self.hardware.cpu_physical_cores
        memory = self.hardware.total_memory_gb
        
        if cores >= 32 and memory >= 64:
            return HardwareTier.INSTITUTIONAL
        elif cores >= 16 and memory >= 32:
            return HardwareTier.EXTREME
        elif cores >= 8 and memory >= 16:
            return HardwareTier.HIGH
        elif cores >= 4 and memory >= 8:
            return HardwareTier.MID
        else:
            return HardwareTier.ENTRY
    
    def _detect_disk_type(self) -> str:
        """Detect disk type (SSD/HDD/NVMe)."""
        try:
            # Check if running on SSD/NVMe
            import subprocess
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'mediatype'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout.lower()
            if 'nvme' in output or 'ssd' in output:
                return 'nvme' if 'nvme' in output else 'ssd'
            elif 'hdd' in output:
                return 'hdd'
        except Exception:
            pass
        
        # Fallback: assume SSD for modern systems
        return 'ssd' if self.hardware.tier != HardwareTier.ENTRY else 'unknown'
    
    def _auto_configure(self) -> None:
        """Auto-configure based on detected hardware."""
        tier = self.hardware.tier
        
        # CPU/Threading
        self.config.num_workers = max(1, self.hardware.cpu_physical_cores - 2)
        self.config.thread_pool_size = self.hardware.cpu_logical_cores
        self.config.cpu_affinity = list(range(self.hardware.cpu_physical_cores))
        
        # Memory
        self.config.max_memory_mb = int(self.hardware.total_memory_gb * 1024 * 0.7)
        self.config.cache_size_mb = int(self.hardware.total_memory_gb * 1024 * 0.1)
        self.config.enable_memory_pooling = tier != HardwareTier.ENTRY
        
        # I/O
        self.config.io_batch_size = 1000 if tier == HardwareTier.ENTRY else 5000
        self.config.async_io_enabled = True
        self.config.disk_cache_enabled = self.hardware.disk_type in ['ssd', 'nvme']
        
        # Backtest
        self.config.parallel_backtest = tier != HardwareTier.ENTRY
        self.config.vectorized_computation = True
        self.config.numba_acceleration = True
        self.config.gpu_acceleration = self.hardware.gpu_available
        
        # AI/ML
        self.config.model_cache_enabled = True
        self.config.gpu_inference = self.hardware.gpu_available
        self.config.model_quantization = True
        
        # Logging
        self.config.log_level = "INFO"
        self.config.metrics_enabled = True
        self.config.tracing_enabled = tier != HardwareTier.ENTRY
        self.config.sampling_rate = 0.1 if tier == HardwareTier.ENTRY else 1.0
        
        self._applied_preset = OptimizationPreset.DEVELOPMENT
        self._log_optimization("auto_configure")
    
    def apply_preset(self, preset: OptimizationPreset) -> None:
        """Apply optimization preset."""
        self._applied_preset = preset
        
        if preset == OptimizationPreset.DEVELOPMENT:
            self._apply_development_preset()
        elif preset == OptimizationPreset.BACKTESTING:
            self._apply_backtesting_preset()
        elif preset == OptimizationPreset.PAPER_TRADING:
            self._apply_paper_trading_preset()
        elif preset == OptimizationPreset.PRODUCTION:
            self._apply_production_preset()
        elif preset == OptimizationPreset.HFT:
            self._apply_hft_preset()
        elif preset == OptimizationPreset.CONSERVATIVE:
            self._apply_conservative_preset()
        
        self._log_optimization(f"apply_preset_{preset.value}")
    
    def _apply_development_preset(self) -> None:
        """Development preset: debug-friendly."""
        self.config.log_level = "DEBUG"
        self.config.num_workers = 2
        self.config.parallel_backtest = False
        self.config.tracing_enabled = True
        self.config.sampling_rate = 1.0
        self.config.process_priority = "normal"
    
    def _apply_backtesting_preset(self) -> None:
        """Backtesting preset: maximize throughput."""
        self.config.num_workers = self.hardware.cpu_physical_cores
        self.config.thread_pool_size = self.hardware.cpu_logical_cores
        self.config.parallel_backtest = True
        self.config.vectorized_computation = True
        self.config.numba_acceleration = True
        self.config.gpu_acceleration = self.hardware.gpu_available
        self.config.max_memory_mb = int(self.hardware.total_memory_gb * 1024 * 0.8)
        self.config.cache_size_mb = int(self.hardware.total_memory_gb * 1024 * 0.2)
        self.config.process_priority = "high"
        self.config.log_level = "WARNING"
    
    def _apply_paper_trading_preset(self) -> None:
        """Paper trading preset: balance performance and safety."""
        self.config.num_workers = max(1, self.hardware.cpu_physical_cores - 2)
        self.config.parallel_backtest = False
        self.config.risk_check_interval_ms = 100
        self.config.max_concurrent_positions = 5
        self.config.log_level = "INFO"
        self.config.metrics_enabled = True
        self.config.process_priority = "normal"
    
    def _apply_production_preset(self) -> None:
        """Production preset: maximum performance and reliability."""
        self.config.num_workers = self.hardware.cpu_physical_cores
        self.config.thread_pool_size = self.hardware.cpu_logical_cores
        self.config.parallel_backtest = True
        self.config.vectorized_computation = True
        self.config.numba_acceleration = True
        self.config.gpu_acceleration = self.hardware.gpu_available
        self.config.max_memory_mb = int(self.hardware.total_memory_gb * 1024 * 0.7)
        self.config.cache_size_mb = int(self.hardware.total_memory_gb * 1024 * 0.15)
        self.config.process_priority = "high"
        self.config.log_level = "WARNING"
        self.config.metrics_enabled = True
        self.config.tracing_enabled = True
        self.config.sampling_rate = 0.5
        self.config.risk_check_interval_ms = 50
        self.config.max_concurrent_positions = 10
        
        # CPU affinity for performance
        try:
            process = psutil.Process()
            process.cpu_affinity(list(range(self.hardware.cpu_physical_cores)))
        except Exception:
            pass
    
    def _apply_hft_preset(self) -> None:
        """HFT preset: ultra-low latency."""
        self.config.num_workers = self.hardware.cpu_physical_cores // 2
        self.config.thread_pool_size = 2  # Minimal threads for determinism
        self.config.parallel_backtest = False
        self.config.vectorized_computation = True
        self.config.numba_acceleration = True
        self.config.gpu_acceleration = self.hardware.gpu_available
        self.config.max_memory_mb = int(self.hardware.total_memory_gb * 1024 * 0.5)
        self.config.cache_size_mb = int(self.hardware.total_memory_gb * 1024 * 0.3)
        self.config.process_priority = "realtime"
        self.config.log_level = "ERROR"
        self.config.metrics_enabled = True
        self.config.tracing_enabled = False  # Disable tracing for latency
        self.config.risk_check_interval_ms = 10
        self.config.order_batch_size = 1
        self.config.io_batch_size = 1
        self.config.async_io_enabled = False  # Sync for determinism
        
        # Isolate CPU cores
        try:
            process = psutil.Process()
            process.cpu_affinity([0, 1])  # Use only first 2 cores
        except Exception:
            pass
    
    def _apply_conservative_preset(self) -> None:
        """Conservative preset: resource-limited, safe."""
        self.config.num_workers = 2
        self.config.thread_pool_size = 2
        self.config.parallel_backtest = False
        self.config.max_memory_mb = 2048
        self.config.cache_size_mb = 256
        self.config.max_concurrent_positions = 3
        self.config.risk_check_interval_ms = 200
        self.config.log_level = "DEBUG"
        self.config.process_priority = "low"
    
    def _log_optimization(self, action: str) -> None:
        """Log optimization action."""
        self._optimization_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'preset': self._applied_preset.value if self._applied_preset else None,
            'hardware_tier': self.hardware.tier.value
        })
    
    def get_optimized_config(self) -> OptimizationConfig:
        """Get current optimized configuration."""
        return self.config
    
    def get_hardware_info(self) -> HardwareInfo:
        """Get detected hardware information."""
        return self.hardware
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report."""
        return {
            'hardware': {
                'cpu_count': self.hardware.cpu_count,
                'cpu_physical_cores': self.hardware.cpu_physical_cores,
                'cpu_logical_cores': self.hardware.cpu_logical_cores,
                'cpu_frequency_ghz': self.hardware.cpu_frequency_ghz,
                'memory_gb': self.hardware.total_memory_gb,
                'gpu_available': self.hardware.gpu_available,
                'gpu_count': self.hardware.gpu_count,
                'disk_type': self.hardware.disk_type,
                'tier': self.hardware.tier.value
            },
            'optimization': {
                'preset': self._applied_preset.value if self._applied_preset else 'custom',
                'num_workers': self.config.num_workers,
                'max_memory_mb': self.config.max_memory_mb,
                'parallel_backtest': self.config.parallel_backtest,
                'gpu_acceleration': self.config.gpu_acceleration,
                'vectorized_computation': self.config.vectorized_computation,
                'numba_acceleration': self.config.numba_acceleration
            },
            'history': self._optimization_history[-10:]
        }
    
    def save_config(self, path: str) -> None:
        """Save configuration to file."""
        config_dict = {
            'hardware': {
                'cpu_count': self.hardware.cpu_count,
                'cpu_physical_cores': self.hardware.cpu_physical_cores,
                'cpu_logical_cores': self.hardware.cpu_logical_cores,
                'total_memory_gb': self.hardware.total_memory_gb,
                'gpu_available': self.hardware.gpu_available,
                'disk_type': self.hardware.disk_type,
                'tier': self.hardware.tier.value
            },
            'optimization': {
                'num_workers': self.config.num_workers,
                'cpu_affinity': self.config.cpu_affinity,
                'thread_pool_size': self.config.thread_pool_size,
                'process_priority': self.config.process_priority,
                'max_memory_mb': self.config.max_memory_mb,
                'cache_size_mb': self.config.cache_size_mb,
                'enable_memory_pooling': self.config.enable_memory_pooling,
                'io_batch_size': self.config.io_batch_size,
                'async_io_enabled': self.config.async_io_enabled,
                'disk_cache_enabled': self.config.disk_cache_enabled,
                'parallel_backtest': self.config.parallel_backtest,
                'vectorized_computation': self.config.vectorized_computation,
                'numba_acceleration': self.config.numba_acceleration,
                'gpu_acceleration': self.config.gpu_acceleration,
                'order_batch_size': self.config.order_batch_size,
                'risk_check_interval_ms': self.config.risk_check_interval_ms,
                'log_level': self.config.log_level,
                'metrics_enabled': self.config.metrics_enabled,
                'tracing_enabled': self.config.tracing_enabled,
                'model_cache_enabled': self.config.model_cache_enabled,
                'gpu_inference': self.config.gpu_inference,
                'max_concurrent_positions': self.config.max_concurrent_positions,
                'db_pool_size': self.config.db_pool_size
            },
            'preset': self._applied_preset.value if self._applied_preset else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_config(cls, path: str) -> 'SystemOptimizer':
        """Load configuration from file."""
        optimizer = cls()
        
        path_obj = Path(path)
        if not path_obj.exists():
            return optimizer
        
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            opt_data = data.get('optimization', {})
            optimizer.config.num_workers = opt_data.get('num_workers', optimizer.config.num_workers)
            optimizer.config.thread_pool_size = opt_data.get('thread_pool_size', optimizer.config.thread_pool_size)
            optimizer.config.max_memory_mb = opt_data.get('max_memory_mb', optimizer.config.max_memory_mb)
            optimizer.config.cache_size_mb = opt_data.get('cache_size_mb', optimizer.config.cache_size_mb)
            optimizer.config.parallel_backtest = opt_data.get('parallel_backtest', optimizer.config.parallel_backtest)
            optimizer.config.gpu_acceleration = opt_data.get('gpu_acceleration', optimizer.config.gpu_acceleration)
            optimizer.config.log_level = opt_data.get('log_level', optimizer.config.log_level)
            
            preset_name = data.get('preset')
            if preset_name:
                try:
                    optimizer._applied_preset = OptimizationPreset(preset_name)
                except ValueError:
                    pass
        except Exception:
            pass
        
        return optimizer
    
    def print_report(self) -> None:
        """Print optimization report to console."""
        hw = self.hardware
        opt = self.config
        
        print("\n" + "=" * 60)
        print("  ANATOLIAX SYSTEM OPTIMIZATION REPORT")
        print("=" * 60)
        
        print("\nHARDWARE DETECTED:")
        print(f"   CPU: {hw.cpu_physical_cores} cores / {hw.cpu_logical_cores} threads")
        print(f"   Frequency: {hw.cpu_frequency_ghz:.2f} GHz")
        print(f"   Memory: {hw.total_memory_gb:.1f} GB")
        print(f"   GPU: {'Yes' if hw.gpu_available else 'No'} ({hw.gpu_count} devices)")
        print(f"   Disk: {hw.disk_type.upper()}")
        print(f"   Tier: {hw.tier.value.upper()}")
        
        print("\nOPTIMIZATION SETTINGS:")
        print(f"   Preset: {self._applied_preset.value if self._applied_preset else 'custom'}")
        print(f"   Workers: {opt.num_workers}")
        print(f"   Max Memory: {opt.max_memory_mb} MB")
        print(f"   Parallel Backtest: {'Yes' if opt.parallel_backtest else 'No'}")
        print(f"   GPU Acceleration: {'Yes' if opt.gpu_acceleration else 'No'}")
        print(f"   Vectorized Computation: {'Yes' if opt.vectorized_computation else 'No'}")
        print(f"   Numba Acceleration: {'Yes' if opt.numba_acceleration else 'No'}")
        
        print("\nRECOMMENDATIONS:")
        tier = hw.tier.value
        if tier == 'entry':
            print("   Entry-level hardware detected. Consider upgrading for better performance.")
        elif tier == 'mid':
            print("   Mid-tier hardware. Good for paper trading and small-scale backtesting.")
        elif tier == 'high':
            print("   High-end hardware. Suitable for production trading.")
        elif tier in ['extreme', 'institutional']:
            print("   Institutional-grade hardware. Maximum performance enabled.")
        
        if not opt.gpu_acceleration and hw.gpu_available:
            print("   GPU available but not enabled. Consider enabling GPU acceleration.")
        
        print("\n" + "=" * 60)


# Global instance
_system_optimizer: Optional[SystemOptimizer] = None


def get_system_optimizer() -> SystemOptimizer:
    """Get global system optimizer instance."""
    global _system_optimizer
    if _system_optimizer is None:
        _system_optimizer = SystemOptimizer.auto_configure()
    return _system_optimizer


def apply_optimization_preset(preset: str) -> SystemOptimizer:
    """Apply optimization preset globally."""
    optimizer = get_system_optimizer()
    optimizer.apply_preset(OptimizationPreset(preset))
    return optimizer


# Convenience functions
def optimize_for_production() -> SystemOptimizer:
    """Apply production optimization preset."""
    return apply_optimization_preset('production')


def optimize_for_backtesting() -> SystemOptimizer:
    """Apply backtesting optimization preset."""
    return apply_optimization_preset('backtesting')


def optimize_for_hft() -> SystemOptimizer:
    """Apply HFT optimization preset."""
    return apply_optimization_preset('hft')


def optimize_for_development() -> SystemOptimizer:
    """Apply development optimization preset."""
    return apply_optimization_preset('development')


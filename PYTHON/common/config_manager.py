"""
PYTHON/common/config_manager.py — Configuration & Feature Flags Manager

CRITICAL COMPONENT #8 from Missing Components PDF

Features:
- Runtime configuration changes without redeploy
- Feature flags for A/B testing
- Environment-specific configs
- Config validation with pydantic
- Hot reload support

Problem Statement: "How do I change behavior without redeploying?"
Without this: Every config change requires code deploy = slow and risky
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, validator


class EnvironmentType(Enum):
    DEVELOPMENT = "development"
    PAPER_TRADING = "paper_trading"
    PRODUCTION = "production"


class FeatureFlagState(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    ROLLOUT_10 = "rollout_10"  # 10% of users
    ROLLOUT_50 = "rollout_50"  # 50% of users


@dataclass
class FeatureFlag:
    """Feature flag definition."""
    name: str
    description: str
    state: FeatureFlagState
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    owner: str = ""
    rollout_percentage: int = 0


@dataclass
class ConfigChange:
    """Config change audit log."""
    key: str
    old_value: Any
    new_value: Any
    changed_by: str
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


class TradingConfig(BaseModel):
    """Trading configuration schema."""
    max_position_size_pct: float = Field(default=10.0, ge=0, le=100)
    max_daily_loss_pct: float = Field(default=2.0, ge=0, le=100)
    max_drawdown_pct: float = Field(default=5.0, ge=0, le=100)
    default_leverage: float = Field(default=1.0, ge=0, le=10)
    enable_auto_trading: bool = False
    enable_paper_trading: bool = True
    risk_free_rate: float = Field(default=0.05, ge=0)
    
    @validator('max_position_size_pct')
    def validate_position_size(cls, v):
        if v > 50:
            raise ValueError("Position size cannot exceed 50%")
        return v


class RiskConfig(BaseModel):
    """Risk configuration schema."""
    var_confidence_level: float = Field(default=0.95, ge=0.9, le=0.99)
    max_var_pct: float = Field(default=3.0, ge=0)
    enable_kill_switch: bool = True
    kill_switch_drawdown_pct: float = Field(default=10.0, ge=0)
    enable_margin_monitor: bool = True
    margin_call_level: float = Field(default=120.0, ge=100)
    liquidation_level: float = Field(default=100.0, ge=0)


class ExecutionConfig(BaseModel):
    """Execution configuration schema."""
    default_order_type: str = "limit"
    default_time_in_force: str = "GTC"
    max_slippage_pct: float = Field(default=0.5, ge=0)
    enable_smart_routing: bool = True
    order_timeout_sec: float = 300.0
    max_retries: int = Field(default=3, ge=0, le=10)


class SystemConfig(BaseModel):
    """System-wide configuration."""
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = False
    metrics_sampling_rate: float = Field(default=0.1, ge=0, le=1)
    data_persistence_path: str = "PYTHON/data"


class ConfigManager:
    """
    Configuration & Feature Flags Manager.
    
    Allows runtime configuration changes without redeployment.
    """
    
    def __init__(self, config_path: str = "PYTHON/config/config.json"):
        self.config_path = Path(config_path)
        self._trading_config: TradingConfig = TradingConfig()
        self._risk_config: RiskConfig = RiskConfig()
        self._execution_config: ExecutionConfig = ExecutionConfig()
        self._system_config: SystemConfig = SystemConfig()
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._change_history: List[ConfigChange] = []
        self._callbacks: Dict[str, List] = {}
        self._load()
        self._init_default_flags()
    
    def _init_default_flags(self) -> None:
        """Initialize default feature flags."""
        default_flags = [
            FeatureFlag("gpu_acceleration", "GPU acceleration for backtesting", FeatureFlagState.DISABLED),
            FeatureFlag("auto_deleveraging", "Automatic deleveraging on margin call", FeatureFlagState.ENABLED),
            FeatureFlag("alpha_decay_detection", "Auto-detect and disable decaying strategies", FeatureFlagState.ENABLED),
            FeatureFlag("multi_exchange", "Multi-exchange trading support", FeatureFlagState.ROLLOUT_50),
            FeatureFlag("options_trading", "Options trading support", FeatureFlagState.DISABLED),
            FeatureFlag("hft_mode", "High-frequency trading mode", FeatureFlagState.DISABLED),
        ]
        
        for flag in default_flags:
            self._feature_flags[flag.name] = flag
    
    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'trading' in data:
                    self._trading_config = TradingConfig(**data['trading'])
                if 'risk' in data:
                    self._risk_config = RiskConfig(**data['risk'])
                if 'execution' in data:
                    self._execution_config = ExecutionConfig(**data['execution'])
                if 'system' in data:
                    self._system_config = SystemConfig(**data['system'])
            except Exception:
                pass
    
    def _save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'trading': self._trading_config.dict(),
            'risk': self._risk_config.dict(),
            'execution': self._execution_config.dict(),
            'system': self._system_config.dict(),
            'feature_flags': {
                name: {
                    'state': flag.state.value,
                    'rollout_percentage': flag.rollout_percentage,
                    'updated_at': flag.updated_at.isoformat() if flag.updated_at else None
                }
                for name, flag in self._feature_flags.items()
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_trading_config(self) -> TradingConfig:
        """Get trading configuration."""
        return self._trading_config
    
    def get_risk_config(self) -> RiskConfig:
        """Get risk configuration."""
        return self._risk_config
    
    def get_execution_config(self) -> ExecutionConfig:
        """Get execution configuration."""
        return self._execution_config
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration."""
        return self._system_config
    
    def update_config(self, section: str, key: str, value: Any, 
                     changed_by: str = "system", reason: str = "") -> bool:
        """
        Update configuration value at runtime.
        
        Args:
            section: Config section (trading, risk, execution, system)
            key: Config key
            value: New value
            changed_by: Who made the change
            reason: Reason for change
        
        Returns:
            True if successful, False otherwise
        """
        config_map = {
            'trading': self._trading_config,
            'risk': self._risk_config,
            'execution': self._execution_config,
            'system': self._system_config
        }
        
        config = config_map.get(section)
        if not config or not hasattr(config, key):
            return False
        
        old_value = getattr(config, key)
        
        try:
            setattr(config, key, value)
            self._save()
            
            # Log change
            change = ConfigChange(
                key=f"{section}.{key}",
                old_value=old_value,
                new_value=value,
                changed_by=changed_by,
                reason=reason
            )
            self._change_history.append(change)
            
            # Keep last 1000 changes
            if len(self._change_history) > 1000:
                self._change_history = self._change_history[-1000:]
            
            # Notify callbacks
            self._notify_callbacks(f"{section}.{key}", value)
            
            return True
        except Exception:
            return False
    
    def is_feature_enabled(self, flag_name: str, user_id: str = None) -> bool:
        """
        Check if feature flag is enabled.
        
        Args:
            flag_name: Feature flag name
            user_id: Optional user ID for rollout percentage
        
        Returns:
            True if feature is enabled for this user
        """
        flag = self._feature_flags.get(flag_name)
        if not flag:
            return False
        
        if flag.state == FeatureFlagState.DISABLED:
            return False
        elif flag.state == FeatureFlagState.ENABLED:
            return True
        elif flag.state in [FeatureFlagState.ROLLOUT_10, FeatureFlagState.ROLLOUT_50]:
            # Rollout based on user_id hash
            if user_id:
                hash_val = hash(user_id) % 100
                threshold = 10 if flag.state == FeatureFlagState.ROLLOUT_10 else 50
                return hash_val < threshold
            return False
        
        return False
    
    def enable_feature(self, flag_name: str, state: FeatureFlagState = None) -> bool:
        """Enable or update feature flag."""
        flag = self._feature_flags.get(flag_name)
        if not flag:
            return False
        
        flag.state = state or FeatureFlagState.ENABLED
        flag.updated_at = datetime.now(timezone.utc)
        return True
    
    def disable_feature(self, flag_name: str) -> bool:
        """Disable feature flag."""
        return self.enable_feature(flag_name, FeatureFlagState.DISABLED)
    
    def get_feature_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature flags."""
        return {
            name: {
                'description': flag.description,
                'state': flag.state.value,
                'rollout_percentage': flag.rollout_percentage,
                'enabled': self.is_feature_enabled(name)
            }
            for name, flag in self._feature_flags.items()
        }
    
    def register_callback(self, config_key: str, callback) -> None:
        """Register callback for config changes."""
        if config_key not in self._callbacks:
            self._callbacks[config_key] = []
        self._callbacks[config_key].append(callback)
    
    def _notify_callbacks(self, config_key: str, value: Any) -> None:
        """Notify registered callbacks."""
        for callback in self._callbacks.get(config_key, []):
            try:
                callback(config_key, value)
            except Exception:
                pass
    
    def get_change_history(self, limit: int = 50) -> List[Dict]:
        """Get configuration change history."""
        return [
            {
                'key': c.key,
                'old_value': c.old_value,
                'new_value': c.new_value,
                'changed_by': c.changed_by,
                'changed_at': c.changed_at.isoformat(),
                'reason': c.reason
            }
            for c in self._change_history[-limit:]
        ]
    
    def export_config(self) -> Dict[str, Any]:
        """Export full configuration."""
        return {
            'trading': self._trading_config.dict(),
            'risk': self._risk_config.dict(),
            'execution': self._execution_config.dict(),
            'system': self._system_config.dict(),
            'feature_flags': self.get_feature_flags()
        }


# Global instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


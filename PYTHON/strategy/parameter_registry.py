"""
parameter_registry.py — Unified Parameter Registry (K95)

Regime-specific, symbol-specific, tier-specific parameter trees.
Injected into SignalEngine, BacktestEngine, and GoldMiningOrchestrator.

Usage:
    from strategy.parameter_registry import ParameterRegistry, SignalConfig
    reg = ParameterRegistry()
    cfg = reg.get_signal_config(regime="BULL", symbol="THYAO")
    print(cfg.rsi_weights)  # regime-adaptive
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from enum import Enum


class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    LOW_VOL = "low_vol"


@dataclass
class SignalConfig:
    """Configurable signal scoring parameters."""
    ema_weight: float = 0.20
    rsi_weight: float = 0.20
    volume_weight: float = 0.20
    bb_weight: float = 0.15
    vwap_weight: float = 0.15
    macd_weight: float = 0.10

    # Thresholds
    rsi_lower: float = 45.0
    rsi_upper: float = 65.0
    volume_z_threshold: float = 2.5
    vwap_deviation_max: float = 0.02
    score_strong: float = 70.0
    score_moderate: float = 55.0
    score_weak: float = 40.0

    # ATR multipliers
    atr_sl_mult: float = 2.0
    atr_tp1_mult: float = 3.0
    atr_tp2_mult: float = 4.0

    # Kelly assumptions
    kelly_win_rate: float = 0.60
    kelly_avg_win: float = 0.04
    kelly_avg_loss: float = 0.02

    # Macro/news penalties
    bear_penalty: float = -10.0
    news_severe_penalty: float = -8.0
    news_moderate_penalty: float = -4.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ema_weight": self.ema_weight,
            "rsi_weight": self.rsi_weight,
            "volume_weight": self.volume_weight,
            "bb_weight": self.bb_weight,
            "vwap_weight": self.vwap_weight,
            "macd_weight": self.macd_weight,
            "rsi_lower": self.rsi_lower,
            "rsi_upper": self.rsi_upper,
            "volume_z_threshold": self.volume_z_threshold,
            "vwap_deviation_max": self.vwap_deviation_max,
            "score_strong": self.score_strong,
            "score_moderate": self.score_moderate,
            "score_weak": self.score_weak,
            "atr_sl_mult": self.atr_sl_mult,
            "atr_tp1_mult": self.atr_tp1_mult,
            "atr_tp2_mult": self.atr_tp2_mult,
            "kelly_win_rate": self.kelly_win_rate,
            "kelly_avg_win": self.kelly_avg_win,
            "kelly_avg_loss": self.kelly_avg_loss,
            "bear_penalty": self.bear_penalty,
            "news_severe_penalty": self.news_severe_penalty,
            "news_moderate_penalty": self.news_moderate_penalty,
        }


@dataclass
class RiskConfig:
    """Risk engine configurable parameters."""
    max_drawdown_pct: float = 0.10
    daily_loss_pct: float = 0.05
    consecutive_losses: int = 5
    recovery_timeout: int = 300
    position_size_pct: float = 0.02
    max_risk_per_trade_pct: float = 0.02
    kelly_fraction: float = 0.25


@dataclass
class GoldMiningConfig:
    """Gold Mining tier parameters."""
    graduation_multiplier: float = 1.0
    fallback_drawdown_pct: float = 0.05
    max_agents_active: int = 3


class ParameterRegistry:
    """
    Unified parameter registry with regime-based overrides.

    Usage:
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="BULL", symbol="THYAO")
        risk_cfg = reg.get_risk_config(regime="BEAR")
    """

    DEFAULT_SIGNAL = SignalConfig()

    REGIME_OVERRIDES: Dict[str, Dict[str, Any]] = {
        "bull": {
            "ema_weight": 0.25,
            "rsi_weight": 0.15,
            "volume_weight": 0.25,
            "bb_weight": 0.10,
            "vwap_weight": 0.15,
            "macd_weight": 0.10,
            "rsi_lower": 50.0,
            "rsi_upper": 75.0,
            "volume_z_threshold": 2.0,
            "atr_sl_mult": 2.5,
            "atr_tp1_mult": 4.0,
            "atr_tp2_mult": 5.0,
            "kelly_win_rate": 0.65,
            "kelly_avg_win": 0.05,
            "bear_penalty": -5.0,
        },
        "bear": {
            "ema_weight": 0.15,
            "rsi_weight": 0.25,
            "volume_weight": 0.20,
            "bb_weight": 0.20,
            "vwap_weight": 0.10,
            "macd_weight": 0.10,
            "rsi_lower": 30.0,
            "rsi_upper": 50.0,
            "volume_z_threshold": 3.0,
            "atr_sl_mult": 1.5,
            "atr_tp1_mult": 2.0,
            "atr_tp2_mult": 3.0,
            "kelly_win_rate": 0.55,
            "kelly_avg_loss": 0.03,
            "bear_penalty": -15.0,
            "news_severe_penalty": -12.0,
        },
        "sideways": {
            "ema_weight": 0.20,
            "rsi_weight": 0.25,
            "volume_weight": 0.15,
            "bb_weight": 0.25,
            "vwap_weight": 0.10,
            "macd_weight": 0.05,
            "rsi_lower": 40.0,
            "rsi_upper": 60.0,
            "volume_z_threshold": 2.0,
            "atr_sl_mult": 1.5,
            "atr_tp1_mult": 2.5,
            "atr_tp2_mult": 3.5,
        },
        "volatile": {
            "ema_weight": 0.15,
            "rsi_weight": 0.20,
            "volume_weight": 0.30,
            "bb_weight": 0.15,
            "vwap_weight": 0.10,
            "macd_weight": 0.10,
            "volume_z_threshold": 3.5,
            "atr_sl_mult": 3.0,
            "atr_tp1_mult": 5.0,
            "atr_tp2_mult": 7.0,
        },
        "low_vol": {
            "ema_weight": 0.25,
            "rsi_weight": 0.20,
            "volume_weight": 0.10,
            "bb_weight": 0.20,
            "vwap_weight": 0.20,
            "macd_weight": 0.05,
            "volume_z_threshold": 1.5,
            "atr_sl_mult": 1.5,
            "atr_tp1_mult": 2.5,
            "atr_tp2_mult": 3.5,
        },
    }

    DEFAULT_RISK = RiskConfig()

    RISK_OVERRIDES: Dict[str, Dict[str, Any]] = {
        "bull": {"max_drawdown_pct": 0.12, "daily_loss_pct": 0.06, "position_size_pct": 0.025},
        "bear": {"max_drawdown_pct": 0.07, "daily_loss_pct": 0.03, "position_size_pct": 0.015, "kelly_fraction": 0.15},
        "sideways": {"max_drawdown_pct": 0.08, "daily_loss_pct": 0.04, "position_size_pct": 0.02},
        "volatile": {"max_drawdown_pct": 0.05, "daily_loss_pct": 0.02, "position_size_pct": 0.01, "kelly_fraction": 0.15},
        "low_vol": {"max_drawdown_pct": 0.12, "daily_loss_pct": 0.06, "position_size_pct": 0.03},
    }

    def __init__(self):
        self._symbol_overrides: Dict[str, Dict[str, Any]] = {}

    def register_symbol_override(self, symbol: str, **kwargs):
        """Sembol bazli parametre override kaydet."""
        self._symbol_overrides[symbol.upper()] = kwargs

    def get_signal_config(self, regime: str = "sideways", symbol: str | None = None) -> SignalConfig:
        """Regime + symbol override ile SignalConfig dondur."""
        base = self.DEFAULT_SIGNAL.to_dict()
        regime_lower = regime.lower()

        # 1. Regime override
        if regime_lower in self.REGIME_OVERRIDES:
            base.update(self.REGIME_OVERRIDES[regime_lower])

        # 2. Symbol override
        if symbol and symbol.upper() in self._symbol_overrides:
            base.update(self._symbol_overrides[symbol.upper()])

        return SignalConfig(**base)

    def get_risk_config(self, regime: str = "sideways") -> RiskConfig:
        """Regime bazli RiskConfig dondur."""
        base = {
            "max_drawdown_pct": self.DEFAULT_RISK.max_drawdown_pct,
            "daily_loss_pct": self.DEFAULT_RISK.daily_loss_pct,
            "consecutive_losses": self.DEFAULT_RISK.consecutive_losses,
            "recovery_timeout": self.DEFAULT_RISK.recovery_timeout,
            "position_size_pct": self.DEFAULT_RISK.position_size_pct,
            "max_risk_per_trade_pct": self.DEFAULT_RISK.max_risk_per_trade_pct,
            "kelly_fraction": self.DEFAULT_RISK.kelly_fraction,
        }
        regime_lower = regime.lower()
        if regime_lower in self.RISK_OVERRIDES:
            base.update(self.RISK_OVERRIDES[regime_lower])
        return RiskConfig(**base)

    def get_gold_mining_config(self) -> GoldMiningConfig:
        return GoldMiningConfig()


# Global singleton for convenience
_GLOBAL_REGISTRY: Optional[ParameterRegistry] = None


def get_registry() -> ParameterRegistry:
    """Global parameter registry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ParameterRegistry()
    return _GLOBAL_REGISTRY

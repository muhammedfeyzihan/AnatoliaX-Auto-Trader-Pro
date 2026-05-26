"""
Test: PYTHON.strategy.parameter_registry
ParameterRegistry, SignalConfig, RiskConfig, GoldMiningConfig dogrulama.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategy.parameter_registry import (
    MarketRegime,
    SignalConfig,
    RiskConfig,
    GoldMiningConfig,
    ParameterRegistry,
    get_registry,
)


class TestSignalConfig:
    def test_default_values(self):
        cfg = SignalConfig()
        assert cfg.ema_weight == 0.20
        assert cfg.rsi_weight == 0.20
        assert cfg.volume_weight == 0.20
        assert cfg.bb_weight == 0.15
        assert cfg.vwap_weight == 0.15
        assert cfg.macd_weight == 0.10
        assert cfg.rsi_lower == 45.0
        assert cfg.rsi_upper == 65.0
        assert cfg.volume_z_threshold == 2.5
        assert cfg.vwap_deviation_max == 0.02
        assert cfg.score_strong == 70.0
        assert cfg.score_moderate == 55.0
        assert cfg.score_weak == 40.0
        assert cfg.atr_sl_mult == 2.0
        assert cfg.atr_tp1_mult == 3.0
        assert cfg.atr_tp2_mult == 4.0
        assert cfg.kelly_win_rate == 0.60
        assert cfg.kelly_avg_win == 0.04
        assert cfg.kelly_avg_loss == 0.02
        assert cfg.bear_penalty == -10.0
        assert cfg.news_severe_penalty == -8.0
        assert cfg.news_moderate_penalty == -4.0

    def test_to_dict(self):
        cfg = SignalConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["ema_weight"] == 0.20
        assert d["rsi_weight"] == 0.20
        assert "score_strong" in d
        assert "bear_penalty" in d

    def test_custom_override(self):
        cfg = SignalConfig(ema_weight=0.30, rsi_lower=50.0, atr_sl_mult=2.5)
        assert cfg.ema_weight == 0.30
        assert cfg.rsi_lower == 50.0
        assert cfg.atr_sl_mult == 2.5
        assert cfg.rsi_weight == 0.20  # default preserved


class TestRiskConfig:
    def test_default_values(self):
        cfg = RiskConfig()
        assert cfg.max_drawdown_pct == 0.10
        assert cfg.daily_loss_pct == 0.05
        assert cfg.consecutive_losses == 5
        assert cfg.recovery_timeout == 300
        assert cfg.position_size_pct == 0.02
        assert cfg.max_risk_per_trade_pct == 0.02
        assert cfg.kelly_fraction == 0.25


class TestGoldMiningConfig:
    def test_default_values(self):
        cfg = GoldMiningConfig()
        assert cfg.graduation_multiplier == 1.0
        assert cfg.fallback_drawdown_pct == 0.05
        assert cfg.max_agents_active == 3


class TestParameterRegistry:
    def test_get_signal_config_default(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config()
        assert isinstance(cfg, SignalConfig)
        assert cfg.ema_weight == SignalConfig().ema_weight

    def test_get_signal_config_bull(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="BULL")
        assert cfg.ema_weight == 0.25
        assert cfg.rsi_weight == 0.15
        assert cfg.volume_weight == 0.25
        assert cfg.rsi_lower == 50.0
        assert cfg.rsi_upper == 75.0
        assert cfg.atr_sl_mult == 2.5
        assert cfg.atr_tp1_mult == 4.0
        assert cfg.kelly_win_rate == 0.65
        assert cfg.bear_penalty == -5.0

    def test_get_signal_config_bear(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="BEAR")
        assert cfg.ema_weight == 0.15
        assert cfg.rsi_weight == 0.25
        assert cfg.rsi_lower == 30.0
        assert cfg.rsi_upper == 50.0
        assert cfg.atr_sl_mult == 1.5
        assert cfg.atr_tp1_mult == 2.0
        assert cfg.kelly_win_rate == 0.55
        assert cfg.kelly_avg_loss == 0.03
        assert cfg.bear_penalty == -15.0
        assert cfg.news_severe_penalty == -12.0

    def test_get_signal_config_sideways(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="SIDEWAYS")
        assert cfg.ema_weight == 0.20
        assert cfg.rsi_weight == 0.25
        assert cfg.bb_weight == 0.25
        assert cfg.rsi_lower == 40.0
        assert cfg.rsi_upper == 60.0

    def test_get_signal_config_volatile(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="VOLATILE")
        assert cfg.volume_weight == 0.30
        assert cfg.volume_z_threshold == 3.5
        assert cfg.atr_sl_mult == 3.0
        assert cfg.atr_tp1_mult == 5.0
        assert cfg.atr_tp2_mult == 7.0

    def test_get_signal_config_low_vol(self):
        reg = ParameterRegistry()
        cfg = reg.get_signal_config(regime="LOW_VOL")
        assert cfg.volume_weight == 0.10
        assert cfg.volume_z_threshold == 1.5
        assert cfg.vwap_weight == 0.20

    def test_get_signal_config_symbol_override(self):
        reg = ParameterRegistry()
        reg.register_symbol_override("THYAO", ema_weight=0.35, rsi_lower=55.0)
        cfg = reg.get_signal_config(regime="BULL", symbol="THYAO")
        assert cfg.ema_weight == 0.35
        assert cfg.rsi_lower == 55.0
        # Other bull overrides still apply
        assert cfg.rsi_upper == 75.0

    def test_get_signal_config_symbol_override_case_insensitive(self):
        reg = ParameterRegistry()
        reg.register_symbol_override("thyao", ema_weight=0.35)
        cfg = reg.get_signal_config(symbol="ThYaO")
        assert cfg.ema_weight == 0.35

    def test_get_risk_config_default(self):
        reg = ParameterRegistry()
        # Default regime is "sideways" which has max_drawdown_pct=0.08
        cfg = reg.get_risk_config()
        assert isinstance(cfg, RiskConfig)
        assert cfg.max_drawdown_pct == 0.08
        assert cfg.daily_loss_pct == 0.04
        assert cfg.position_size_pct == 0.02

    def test_get_risk_config_bull(self):
        reg = ParameterRegistry()
        cfg = reg.get_risk_config(regime="BULL")
        assert cfg.max_drawdown_pct == 0.12
        assert cfg.daily_loss_pct == 0.06
        assert cfg.position_size_pct == 0.025

    def test_get_risk_config_bear(self):
        reg = ParameterRegistry()
        cfg = reg.get_risk_config(regime="BEAR")
        assert cfg.max_drawdown_pct == 0.07
        assert cfg.daily_loss_pct == 0.03
        assert cfg.position_size_pct == 0.015
        assert cfg.kelly_fraction == 0.15

    def test_get_risk_config_volatile(self):
        reg = ParameterRegistry()
        cfg = reg.get_risk_config(regime="VOLATILE")
        assert cfg.max_drawdown_pct == 0.05
        assert cfg.daily_loss_pct == 0.02
        assert cfg.position_size_pct == 0.01
        assert cfg.kelly_fraction == 0.15

    def test_get_gold_mining_config(self):
        reg = ParameterRegistry()
        cfg = reg.get_gold_mining_config()
        assert isinstance(cfg, GoldMiningConfig)
        assert cfg.max_agents_active == 3

    def test_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_market_regime_enum(self):
        assert MarketRegime.BULL.value == "bull"
        assert MarketRegime.BEAR.value == "bear"
        assert MarketRegime.SIDEWAYS.value == "sideways"
        assert MarketRegime.VOLATILE.value == "volatile"
        assert MarketRegime.LOW_VOL.value == "low_vol"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

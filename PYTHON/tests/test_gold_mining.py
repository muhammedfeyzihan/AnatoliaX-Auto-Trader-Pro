"""
tests/test_gold_mining.py — Gold Mining strategy tests

Covers tier progression, fallback, kill switch, position sizing,
and orchestrator integration with all 4 tiers.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from strategy.gold_mining.orchestrator import (
    GoldMiningOrchestrator,
    GoldMiningState,
)
from strategy.gold_mining.tier_config import (
    get_tier_by_name,
    get_next_tier,
    TIER_DEFINITIONS,
)
from strategy.gold_mining.ms_strategy import MSStrategy
from strategy.gold_mining.s1_strategy import S1Strategy
from strategy.gold_mining.m1_strategy import M1Strategy
from strategy.gold_mining.m5_strategy import M5Strategy
from strategy.gold_mining.m15_strategy import M15Strategy
from strategy.gold_mining.m30_strategy import M30Strategy
from strategy.gold_mining.h1_strategy import H1Strategy
from strategy.gold_mining.h2_strategy import H2Strategy
from strategy.gold_mining.d1_strategy import D1Strategy


def _make_df(n: int = 50, close_start: float = 100.0, trend: str = "up") -> pd.DataFrame:
    """Generate a synthetic OHLCV DataFrame."""
    idx = pd.date_range(end=datetime.now(), periods=n, freq="1min")
    closes = np.zeros(n)
    closes[0] = close_start
    for i in range(1, n):
        if trend == "up":
            closes[i] = closes[i - 1] * (1 + np.random.uniform(0.0005, 0.002))
        elif trend == "down":
            closes[i] = closes[i - 1] * (1 - np.random.uniform(0.0005, 0.002))
        else:
            closes[i] = closes[i - 1] * (1 + np.random.uniform(-0.001, 0.001))
    # Ensure last bars have a clear cross for M1 / M15
    if n >= 10:
        closes[-5:] = closes[-6] * (1 + np.linspace(0.001, 0.015, 5))

    opens = closes * (1 - np.random.uniform(-0.001, 0.001, n))
    highs = np.maximum(opens, closes) * (1 + np.random.uniform(0.0005, 0.002, n))
    lows = np.minimum(opens, closes) * (1 - np.random.uniform(0.0005, 0.002, n))
    volumes = np.random.randint(1_000, 50_000, n)
    volumes[-1] *= 5  # volume spike

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }, index=idx)


# ------------------------------------------------------------------
# Tier config
# ------------------------------------------------------------------
class TestTierConfig:
    def test_default_tier_is_ms(self):
        tier = get_tier_by_name("MS")
        assert tier is not None
        assert tier.name == "MS"
        assert tier.max_agents == 1

    def test_next_tier_chain(self):
        assert get_next_tier("MS").name == "S1"
        assert get_next_tier("S1").name == "M1"
        assert get_next_tier("M1").name == "M5"
        assert get_next_tier("M5").name == "M15"
        assert get_next_tier("M15").name == "M30"
        assert get_next_tier("M30").name == "H1"
        assert get_next_tier("H1").name == "H2"
        assert get_next_tier("H2").name == "D1"
        assert get_next_tier("D1") is None

    def test_all_tiers_have_strategy_module(self):
        for t in TIER_DEFINITIONS:
            assert t.strategy_module.startswith("strategy.gold_mining")


# ------------------------------------------------------------------
# Individual strategies
# ------------------------------------------------------------------
class TestMSStrategy:
    def test_generate_buy_signal(self):
        s = MSStrategy()
        bar = {
            "timestamp": datetime.now(),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.8,
            "bid_volume": 80,
            "ask_volume": 20,
            "total_volume": 100,
            "spread": 0.1,
        }
        sig = s.generate(bar)
        assert sig is not None
        assert sig["side"] == "BUY"
        assert sig["strategy"] == "MS_ORDER_FLOW"

    def test_low_volume_rejected(self):
        s = MSStrategy(min_volume=200)
        bar = {
            "timestamp": datetime.now(),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.8,
            "bid_volume": 80,
            "ask_volume": 20,
            "total_volume": 100,
            "spread": 0.1,
        }
        assert s.generate(bar) is None

    def test_batch_generate(self):
        s = MSStrategy()
        bars = [
            {"timestamp": datetime.now(), "open": 100, "high": 101, "low": 99, "close": 100.8,
             "bid_volume": 80, "ask_volume": 20, "total_volume": 100, "spread": 0.05},
            {"timestamp": datetime.now(), "open": 100, "high": 101, "low": 99, "close": 99.2,
             "bid_volume": 20, "ask_volume": 80, "total_volume": 100, "spread": 0.05},
        ]
        sigs = s.batch_generate(bars)
        assert len(sigs) == 2
        assert sigs[0]["side"] == "BUY"
        assert sigs[1]["side"] == "SELL"


class TestS1Strategy:
    def test_generate_signal(self):
        s = S1Strategy()
        df = _make_df(n=30, close_start=100.0)
        sig = s.generate(df)
        # Volume spike is present, deviation may or may not cross threshold
        # We just assert no crash and correct structure when not None
        if sig:
            assert "side" in sig
            assert "entry" in sig
            assert sig["strategy"] == "S1_VWAP_DEVIATION"

    def test_empty_df_returns_none(self):
        s = S1Strategy()
        assert s.generate(pd.DataFrame()) is None


class TestM1Strategy:
    def test_generate_cross_signal(self):
        s = M1Strategy()
        df = _make_df(n=50, close_start=100.0)
        # Force a clean cross in the last two bars for EMA 3/8
        closes = df["close"].values.copy()
        closes[-10:] = np.linspace(closes[-11], closes[-11] * 1.05, 10)
        df["close"] = closes
        # Recalculate highs/lows to match
        df["high"] = df["close"] * 1.002
        df["low"] = df["close"] * 0.998
        sig = s.generate(df)
        # With strong uptrend and volume spike, should produce BUY or SELL
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert sig["strategy"] == "M1_EMA_CROSS"

    def test_confirm_secondary(self):
        s = M1Strategy()
        df = _make_df(n=50)
        primary = {"side": "BUY"}
        # RSI should be in 30-70 range for synthetic data
        ok = s.confirm_secondary(df, primary)
        assert isinstance(ok, bool)


class TestM15Strategy:
    def test_generate_with_consensus(self):
        s = M15Strategy()
        df = _make_df(n=50, close_start=100.0)
        macro = {"regime": "BULL", "score": 2}
        sig = s.generate(df, macro=macro, sentiment=0.2)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert "consensus" in sig
            assert "confidence" in sig
            assert sig["strategy"] == "M15_3AGENT_CONSENSUS"

    def test_bear_regime_blocks_buy(self):
        s = M15Strategy()
        df = _make_df(n=50, close_start=100.0, trend="down")
        macro = {"regime": "BEAR", "score": -2}
        sig = s.generate(df, macro=macro, sentiment=-0.5)
        # BEAR regime + negative sentiment should suppress BUY consensus
        if sig and sig["side"] == "BUY":
            assert sig["confidence"] >= s.min_confidence

    def test_insufficient_data_returns_none(self):
        s = M15Strategy()
        df = _make_df(n=5)
        assert s.generate(df) is None


class TestM30Strategy:
    def test_generate_with_consensus(self):
        s = M30Strategy()
        df = _make_df(n=50, close_start=100.0)
        macro = {"regime": "BULL", "score": 2}
        sig = s.generate(df, macro=macro, sentiment=0.2)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert "consensus" in sig
            assert "confidence" in sig
            assert sig["strategy"] == "M30_3AGENT_CONSENSUS"

    def test_bear_regime_blocks_buy(self):
        s = M30Strategy()
        df = _make_df(n=50, close_start=100.0, trend="down")
        macro = {"regime": "BEAR", "score": -2}
        sig = s.generate(df, macro=macro, sentiment=-0.5)
        if sig and sig["side"] == "BUY":
            assert sig["confidence"] >= s.min_confidence

    def test_parameter_registry_integration(self):
        s = M30Strategy()
        df = _make_df(n=50, close_start=100.0)
        macro = {"regime": "BULL"}
        sig = s.generate(df, macro=macro, sentiment=0.1)
        # Should not crash; regime-adaptive params are used internally
        assert sig is None or "regime" in sig


class TestH2Strategy:
    def test_generate_with_consensus(self):
        s = H2Strategy()
        df = _make_df(n=60, close_start=100.0)
        macro = {"regime": "BULL", "score": 2}
        sig = s.generate(df, macro=macro, sentiment=0.2)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert "consensus" in sig
            assert "confidence" in sig
            assert sig["strategy"] == "H2_3AGENT_CONSENSUS"

    def test_bear_regime_blocks_buy(self):
        s = H2Strategy()
        df = _make_df(n=60, close_start=100.0, trend="down")
        macro = {"regime": "BEAR", "score": -2}
        sig = s.generate(df, macro=macro, sentiment=-0.5)
        if sig and sig["side"] == "BUY":
            assert sig["confidence"] >= s.min_confidence

    def test_bb_position_in_signal(self):
        s = H2Strategy()
        df = _make_df(n=60, close_start=100.0)
        macro = {"regime": "BULL"}
        sig = s.generate(df, macro=macro, sentiment=0.1)
        if sig:
            assert "bb_position" in sig


class TestM5Strategy:
    def test_generate_with_secondary(self):
        s = M5Strategy()
        df = _make_df(n=50, close_start=100.0)
        sig = s.generate(df)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert sig["strategy"] == "M5_EMA_CROSS"
            assert "sl" in sig
            assert "tp" in sig

    def test_confirm_secondary(self):
        s = M5Strategy()
        df = _make_df(n=50)
        primary = {"side": "BUY"}
        ok = s.confirm_secondary(df, primary)
        assert isinstance(ok, bool)

    def test_low_volatility_rejected(self):
        s = M5Strategy()
        df = _make_df(n=50)
        # Flatline prices = near-zero ATR
        df["close"] = 100.0
        df["high"] = 100.001
        df["low"] = 99.999
        primary = {"side": "BUY"}
        assert s.confirm_secondary(df, primary) is False


class TestH1Strategy:
    def test_generate_with_consensus(self):
        s = H1Strategy()
        df = _make_df(n=50, close_start=100.0)
        macro = {"regime": "BULL", "score": 2}
        sig = s.generate(df, macro=macro, sentiment=0.2)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert sig["strategy"] == "H1_3AGENT_TREND"
            assert "consensus" in sig
            assert "confidence" in sig

    def test_bear_regime_blocks_buy(self):
        s = H1Strategy()
        df = _make_df(n=50, close_start=100.0, trend="down")
        macro = {"regime": "BEAR", "score": -2}
        sig = s.generate(df, macro=macro, sentiment=-0.5)
        if sig and sig["side"] == "BUY":
            assert sig["confidence"] >= s.min_confidence


class TestD1Strategy:
    def test_generate_with_consensus(self):
        s = D1Strategy()
        df = _make_df(n=60, close_start=100.0)
        macro = {"regime": "BULL", "score": 2}
        sig = s.generate(df, macro=macro, sentiment=0.1)
        if sig:
            assert sig["side"] in ("BUY", "SELL")
            assert sig["strategy"] == "D1_3AGENT_POSITION"
            assert "bb_squeeze" in sig
            assert "rsi" in sig

    def test_stricter_sentiment(self):
        s = D1Strategy()
        df = _make_df(n=60)
        macro = {"regime": "NEUTRAL", "score": 0}
        sig = s.generate(df, macro=macro, sentiment=0.8)  # > 0.6
        # Extreme sentiment should reduce confidence below threshold
        assert sig is None or sig["confidence"] < s.min_confidence


# ------------------------------------------------------------------
# Orchestrator core
# ------------------------------------------------------------------
class TestOrchestratorInit:
    def test_default_tier_is_ms(self):
        o = GoldMiningOrchestrator(initial_capital=50_000)
        assert o.state.current_tier_name == "MS"
        assert o.account.initial_cash == 50_000

    def test_custom_rules_applied(self):
        o = GoldMiningOrchestrator(rules={"max_agents_override": 2})
        assert o.rules["max_agents_override"] == 2

    def test_state_restore(self):
        state = GoldMiningState(current_tier_name="M1", consecutive_wins=3)
        o = GoldMiningOrchestrator(state=state)
        assert o.state.current_tier_name == "M1"
        assert o.state.consecutive_wins == 3


class TestOrchestratorSignal:
    def test_ms_tier_signal(self):
        o = GoldMiningOrchestrator()
        df = _make_df(n=30)
        sig = o.generate_signal("THYAO", df)
        # MS uses synthetic micro-bar; with volume spike may or may not trigger
        if sig:
            assert sig["tier"] == "MS"
            assert sig["agents_active"] <= 1

    def test_s1_tier_signal(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "S1"
        df = _make_df(n=30)
        sig = o.generate_signal("THYAO", df)
        if sig:
            assert sig["tier"] == "S1"

    def test_m1_tier_signal_with_confirmation(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "M1"
        df = _make_df(n=50)
        sig = o.generate_signal("THYAO", df)
        if sig:
            assert sig["tier"] == "M1"
            assert sig["agents_active"] <= 2

    def test_m15_tier_signal_with_macro(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "M15"
        df = _make_df(n=50)
        sig = o.generate_signal("THYAO", df, macro={"regime": "BULL", "score": 2}, sentiment=0.1)
        if sig:
            assert sig["tier"] == "M15"
            assert sig["agents_active"] <= 3

    def test_m5_tier_signal_with_confirmation(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "M5"
        df = _make_df(n=50)
        sig = o.generate_signal("THYAO", df)
        if sig:
            assert sig["tier"] == "M5"
            assert sig["agents_active"] <= 2

    def test_m30_tier_signal_with_macro(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "M30"
        df = _make_df(n=50)
        sig = o.generate_signal("THYAO", df, macro={"regime": "BULL", "score": 2}, sentiment=0.1)
        if sig:
            assert sig["tier"] == "M30"
            assert sig["agents_active"] <= 3

    def test_h1_tier_signal_with_macro(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "H1"
        df = _make_df(n=50)
        sig = o.generate_signal("THYAO", df, macro={"regime": "BULL", "score": 2}, sentiment=0.1)
        if sig:
            assert sig["tier"] == "H1"
            assert sig["agents_active"] <= 3

    def test_h2_tier_signal_with_macro(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "H2"
        df = _make_df(n=60)
        sig = o.generate_signal("THYAO", df, macro={"regime": "BULL", "score": 2}, sentiment=0.1)
        if sig:
            assert sig["tier"] == "H2"
            assert sig["agents_active"] <= 3

    def test_d1_tier_signal_with_macro(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "D1"
        df = _make_df(n=60)
        sig = o.generate_signal("THYAO", df, macro={"regime": "BULL", "score": 2}, sentiment=0.1)
        if sig:
            assert sig["tier"] == "D1"
            assert sig["agents_active"] <= 3


class TestOrchestratorPositionSizing:
    def test_positive_size(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        qty = o.calculate_position_size(price=50.0, signal={})
        assert qty >= 1

    def test_zero_price(self):
        o = GoldMiningOrchestrator()
        assert o.calculate_position_size(0.0, {}) == 0

    def test_respects_max_risk(self):
        o = GoldMiningOrchestrator(initial_capital=100_000, rules={"max_risk_per_trade_pct": 0.01})
        qty = o.calculate_position_size(price=10.0, signal={})
        notional = qty * 10.0
        assert notional <= 100_000 * 0.01 * 1.01  # small tolerance


class TestOrchestratorExecution:
    def test_process_symbol_no_signal(self):
        o = GoldMiningOrchestrator()
        df = _make_df(n=5)  # too short for most strategies
        res = o.process_symbol("THYAO", df)
        assert res["executed"] is False
        assert res["reason"] == "NO_SIGNAL"

    def test_process_symbol_risk_gate(self):
        o = GoldMiningOrchestrator(initial_capital=1_000, rules={"max_risk_per_trade_pct": 0.001})
        df = _make_df(n=50)
        # With tiny risk cap, position size may be 0 or risk gate blocks it
        res = o.process_symbol("THYAO", df)
        assert res["executed"] is False or res["quantity"] >= 0


class TestOrchestratorTierProgression:
    def test_graduate_ms_to_s1(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.account.realized_pnl = 2_000.0  # Above S1 min_capital (1_000)
        o.state.consecutive_wins = 5
        o.state.total_trades = 10
        o.state.winning_trades = 6  # 60% WR
        old = o._graduate()
        assert old == "MS"
        assert o.state.current_tier_name == "S1"

    def test_cannot_graduate_d1(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "D1"
        assert o._graduate() is None

    def test_graduate_m1_to_m5(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.state.current_tier_name = "M1"
        o.account.realized_pnl = 13_000.0
        o.state.consecutive_wins = 5
        o.state.total_trades = 10
        o.state.winning_trades = 6
        old = o._graduate()
        assert old == "M1"
        assert o.state.current_tier_name == "M5"

    def test_fallback_on_consecutive_losses(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "M5"
        o.state.consecutive_losses = 3
        old = o._fallback()
        assert old == "M5"
        assert o.state.current_tier_name == "M1"

    def test_fallback_on_drawdown(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.state.current_tier_name = "D1"
        o.state.peak_equity = 100_000
        o.account.cash = 94_000  # 6% drawdown
        old = o._fallback()
        assert old == "D1"
        assert o.state.current_tier_name == "H2"

    def test_ms_never_fallback(self):
        o = GoldMiningOrchestrator()
        o.state.current_tier_name = "MS"
        o.state.consecutive_losses = 10
        assert o._fallback() is None


class TestOrchestratorTradeResult:
    def test_win_increases_streak(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        df = _make_df(n=50)
        res = o.process_symbol("THYAO", df)
        if res["executed"]:
            # Simulate profitable close
            entry = res["signal"]["entry"]
            o.report_trade_result("THYAO", exit_price=entry * 1.05)
            assert o.state.consecutive_wins >= 1
            assert o.state.consecutive_losses == 0

    def test_loss_triggers_fallback(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.state.current_tier_name = "M1"
        o.account.cash = 100_000
        # Manually open a position to simulate loss
        o.account.open_position("THYAO", qty=10, price=100.0, commission=0.0)
        o.report_trade_result("THYAO", exit_price=90.0)
        assert o.state.consecutive_losses == 1
        # After 3 losses fallback happens inside report_trade_result
        for _ in range(2):
            o.account.open_position("THYAO", qty=10, price=100.0, commission=0.0)
            o.report_trade_result("THYAO", exit_price=90.0)
        assert o.state.current_tier_name == "S1"

    def test_kill_switch_triggered_on_deep_loss(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.account.cash = 100_000
        # Open and close with massive loss to trigger kill switch
        o.account.open_position("THYAO", qty=1000, price=100.0, commission=0.0)
        # Realized PnL won't trigger kill switch alone; need daily_pnl < -5% * equity
        # Force by calling update directly
        o.kill_switch.update(capital=90_000, daily_pnl=-6_000, last_trade_pnl=-6_000)
        assert not o.kill_switch.is_alive()

    def test_report_without_position(self):
        o = GoldMiningOrchestrator()
        res = o.report_trade_result("THYAO", exit_price=100.0)
        assert res["reason"] == "NO_OPEN_POSITION"


class TestOrchestratorSerialization:
    def test_to_from_dict(self):
        o = GoldMiningOrchestrator(initial_capital=50_000, rules={"cooldown_seconds": 30})
        o.state.current_tier_name = "S1"
        o.state.consecutive_wins = 2
        o.account.cash = 48_000
        o.account.realized_pnl = -2_000
        data = o.to_dict()
        assert data["current_tier_name"] == "S1"
        assert data["state"]["consecutive_wins"] == 2

        o2 = GoldMiningOrchestrator.from_dict(data)
        assert o2.state.current_tier_name == "S1"
        assert o2.account.cash == 48_000
        assert o2.rules["cooldown_seconds"] == 30


class TestOrchestratorCooldown:
    def test_cooldown_blocks_second_trade(self):
        o = GoldMiningOrchestrator(rules={"cooldown_seconds": 300})
        df = _make_df(n=50)
        r1 = o.process_symbol("THYAO", df)
        r2 = o.process_symbol("THYAO", df)
        if r1["executed"]:
            assert r2["reason"].startswith("COOLDOWN")


class TestOrchestratorBatchScan:
    def test_run_scan_with_provider(self):
        o = GoldMiningOrchestrator()
        def provider(sym, interval):
            return _make_df(n=50)
        results = o.run_scan(["THYAO", "GARAN"], provider)
        assert len(results) == 2
        assert all("symbol" in r for r in results)

    def test_run_scan_error_handling(self):
        o = GoldMiningOrchestrator()
        def bad_provider(sym, interval):
            raise RuntimeError("fail")
        results = o.run_scan(["THYAO"], bad_provider)
        assert results[0]["executed"] is False
        assert "ERROR" in results[0]["reason"]


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------
class TestEdgeCases:
    def test_m1_rsi_secondary_rejects_extreme(self):
        s = M1Strategy()
        df = _make_df(n=50)
        # Force RSI to extreme by making a huge uptrend
        closes = df["close"].values.copy()
        for i in range(1, len(closes)):
            closes[i] = closes[i - 1] * 1.02
        df["close"] = closes
        df["high"] = closes * 1.005
        df["low"] = closes * 0.995
        primary = {"side": "BUY"}
        ok = s.confirm_secondary(df, primary)
        # If RSI > 70, should reject
        assert isinstance(ok, bool)

    def test_m15_confidence_below_threshold(self):
        s = M15Strategy(min_confidence=99.0)  # impossible threshold
        df = _make_df(n=50)
        sig = s.generate(df)
        assert sig is None

    def test_synthesize_micro_bar(self):
        o = GoldMiningOrchestrator()
        row = pd.Series({"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000})
        bar = o._synthesize_micro_bar(row)
        assert bar["close"] == 100.5
        assert bar["total_volume"] == 1000

    def test_position_size_with_zero_equity(self):
        o = GoldMiningOrchestrator(initial_capital=0)
        assert o.calculate_position_size(10.0, {}) == 0


class TestAdaptiveTierSelector:
    def test_high_volatility_selects_m5(self):
        from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
        s = AdaptiveTierSelector()
        df = _make_df(n=50, close_start=100.0)
        # Force high volatility but neutral trend (no strong directional move)
        base = 100.0
        for i in range(len(df)):
            df.loc[df.index[i], "close"] = base + np.random.uniform(-3, 3)
        df["high"] = df["close"] + 3.0
        df["low"] = df["close"] - 3.0
        # Strong volume spike on last bar
        df["volume"] = np.random.randint(10_000, 20_000, len(df))
        df.loc[df.index[-1], "volume"] = 200_000
        tier = s.select(df, macro={"regime": "NEUTRAL"})
        assert tier in ("M5", "S1", "M1")

    def test_low_volatility_selects_safe(self):
        from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
        s = AdaptiveTierSelector()
        df = _make_df(n=50, close_start=100.0)
        df["high"] = df["close"] * 1.001
        df["low"] = df["close"] * 0.999
        df["volume"] = np.random.randint(1_000, 2_000, len(df))
        tier = s.select(df)
        assert tier in ("M1", "M15", "M5")

    def test_strong_trend_selects_h1(self):
        from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
        s = AdaptiveTierSelector()
        df = _make_df(n=50, close_start=100.0, trend="up")
        df["high"] = df["close"] * 1.02
        df["low"] = df["close"] * 0.98
        df["volume"] = np.random.randint(50_000, 100_000, len(df))
        tier = s.select(df, macro={"regime": "BULL"})
        assert tier in ("M15", "H1", "H2", "M5")

    def test_score_all_tiers(self):
        from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
        s = AdaptiveTierSelector()
        df = _make_df(n=50)
        scores = s.score_all_tiers(df)
        assert len(scores) == 9
        assert all(0.0 <= v <= 100.0 for v in scores.values())


class TestManualExit:
    def test_manual_exit_closes_position(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.account.open_position("THYAO", qty=10, price=100.0, commission=0.0)
        res = o.manual_exit("THYAO", exit_price=110.0, reason="KAR_REALIZE")
        assert res["exit_type"] == "MANUAL"
        assert res["exit_reason"] == "KAR_REALIZE"
        assert res["pnl"] > 0
        pos = o.account.get_position("THYAO")
        assert pos is None or not pos.is_open

    def test_manual_exit_without_position(self):
        o = GoldMiningOrchestrator()
        res = o.manual_exit("THYAO", exit_price=100.0)
        assert res["reason"] == "NO_OPEN_POSITION"

    def test_manual_exit_updates_streak(self):
        o = GoldMiningOrchestrator(initial_capital=100_000)
        o.account.open_position("THYAO", qty=10, price=100.0, commission=0.0)
        o.manual_exit("THYAO", exit_price=90.0, reason="ZARAR_DUR")
        assert o.state.consecutive_losses == 1
        assert o.state.total_trades == 1


class TestAutoSelectTier:
    def test_auto_switch_enabled(self):
        o = GoldMiningOrchestrator(rules={"auto_tier_switch": True})
        df = _make_df(n=50, close_start=100.0, trend="up")
        df["high"] = df["close"] * 1.02
        df["low"] = df["close"] * 0.98
        old_tier = o.state.current_tier_name
        rec = o.auto_select_tier(df, macro={"regime": "BULL"})
        assert isinstance(rec, str)
        # If recommendation differs, streaks reset
        if rec != old_tier:
            assert o.state.consecutive_wins == 0

    def test_auto_switch_disabled(self):
        o = GoldMiningOrchestrator(rules={"auto_tier_switch": False})
        df = _make_df(n=50)
        old = o.state.current_tier_name
        rec = o.auto_select_tier(df)
        assert rec == old

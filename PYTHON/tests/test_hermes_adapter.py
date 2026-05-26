"""
Test: hermes_adapter (TA filter + risk gates + skill engine)
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hermes_adapter.ta_filter import TAFPreFilter, TAFilterResult
from hermes_adapter.risk_gates import RiskGateEngine
from hermes_adapter.skill_engine import SkillEngine, Skill


class TestTAFPreFilter:
    def _make_bars(self, trend="up"):
        n = 50
        if trend == "up":
            close = np.linspace(100, 130, n)
        elif trend == "down":
            close = np.linspace(130, 100, n)
        else:
            close = np.ones(n) * 100
        high = close + 1
        low = close - 1
        volume = np.concatenate([np.ones(40) * 1000, np.ones(10) * 3000])
        return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    def test_confirmed_up_trend(self):
        pf = TAFPreFilter(threshold=50)
        bars = {"1d": self._make_bars("up")}
        res = pf.evaluate("THYAO", bars=bars)
        assert isinstance(res, TAFilterResult)
        assert res.symbol == "THYAO"
        assert res.composite_score > 50
        assert res.confirmed is True

    def test_rejected_down_trend(self):
        pf = TAFPreFilter(threshold=50)
        bars = {"1d": self._make_bars("down")}
        res = pf.evaluate("THYAO", bars=bars)
        assert res.confirmed is False

    def test_no_data(self):
        pf = TAFPreFilter()
        res = pf.evaluate("THYAO", bars={})
        assert res.confirmed is False
        assert res.composite_score == 0.0

    def test_multi_timeframe_weighting(self):
        pf = TAFPreFilter(threshold=50)
        bars = {
            "1h": self._make_bars("up"),
            "4h": self._make_bars("up"),
            "1d": self._make_bars("up"),
        }
        res = pf.evaluate("THYAO", bars=bars, timeframes=["1h", "4h", "1d"])
        assert res.confirmed is True
        assert "1d" in res.timeframe_scores


class TestRiskGateEngine:
    def test_all_gates_pass(self):
        engine = RiskGateEngine(market_open_required=False)
        ok, reasons = engine.check_all(
            symbol="THYAO",
            size=10,
            price=100.0,
            side="BUY",
            confidence=70.0,
            sl=95.0,
            tp=110.0,
            open_positions=2,
            portfolio_value=100_000.0,
        )
        assert ok is True
        assert len(reasons) == 0

    def test_confidence_gate_blocks(self):
        engine = RiskGateEngine(min_confidence=80)
        ok, reasons = engine.check_all(
            symbol="THYAO", size=10, price=100.0, side="BUY",
            confidence=50.0, sl=95.0, tp=110.0,
            open_positions=0, portfolio_value=100_000.0,
        )
        assert ok is False
        assert any("CONFIDENCE" in r for r in reasons)

    def test_notional_gate_blocks(self):
        engine = RiskGateEngine(max_notional_per_trade=500.0)
        ok, reasons = engine.check_all(
            symbol="THYAO", size=10, price=100.0, side="BUY",
            confidence=70.0, sl=95.0, tp=110.0,
            open_positions=0, portfolio_value=100_000.0,
        )
        assert ok is False
        assert any("NOTIONAL" in r for r in reasons)

    def test_sl_missing_blocks(self):
        engine = RiskGateEngine(sl_required=True)
        ok, reasons = engine.check_all(
            symbol="THYAO", size=10, price=100.0, side="BUY",
            confidence=70.0, sl=0.0, tp=110.0,
            open_positions=0, portfolio_value=100_000.0,
        )
        assert ok is False
        assert any("SL" in r for r in reasons)

    def test_cooldown_gate(self):
        engine = RiskGateEngine(cooldown_seconds=3600)
        engine.record_trade()
        ok, reasons = engine.check_all(
            symbol="THYAO", size=1, price=100.0, side="BUY",
            confidence=70.0, sl=95.0, tp=110.0,
            open_positions=0, portfolio_value=100_000.0,
        )
        assert ok is False
        assert any("COOLDOWN" in r for r in reasons)


class TestSkillEngine:
    def test_learn_and_retrieve(self, tmp_path):
        engine = SkillEngine(skills_dir=tmp_path)
        # 10+ samples needed for high confidence
        for _ in range(7):
            engine.learn("THYAO", "ema_cross", "win", 500.0)
        for _ in range(3):
            engine.learn("THYAO", "ema_cross", "loss", -200.0)
        skill = engine.get_best_skill("THYAO", min_confidence=50.0)
        assert skill is not None
        assert skill.setup == "ema_cross"
        assert skill.wins == 7
        assert skill.losses == 3

    def test_best_skill_filters_low_confidence(self, tmp_path):
        engine = SkillEngine(skills_dir=tmp_path)
        engine.learn("THYAO", "weak_setup", "loss", -100.0)
        skill = engine.get_best_skill("THYAO", min_confidence=50.0)
        # Low sample size → confidence low → filtered
        assert skill is None or skill.confidence < 50.0

    def test_skill_stats(self, tmp_path):
        engine = SkillEngine(skills_dir=tmp_path)
        engine.learn("THYAO", "setup_a", "win", 100.0)
        engine.learn("GARAN", "setup_b", "win", 200.0)
        stats = engine.get_skill_stats()
        assert stats["total_skills"] == 2
        assert stats["total_wins"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

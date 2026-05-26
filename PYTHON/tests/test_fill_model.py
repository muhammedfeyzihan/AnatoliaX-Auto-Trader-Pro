"""
Test: PYTHON.backtest.fill_model
ImmediateFillModel, ThreeTierFillModel.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.fill_model import ImmediateFillModel, ThreeTierFillModel


class TestImmediateFillModel:
    def test_always_fills(self):
        m = ImmediateFillModel()
        assert m.can_fill(100.0, "BUY", 100) is True
        assert m.fill_price(100.0, "BUY", 100) == 100.0

    def test_fill_price_unchanged(self):
        m = ImmediateFillModel()
        assert m.fill_price(105.0, "SELL", 50) == 105.0


class TestThreeTierFillModel:
    def test_can_fill_deterministic(self):
        m = ThreeTierFillModel(seed=42)
        results = [m.can_fill(100.0, "BUY", 100) for _ in range(100)]
        assert any(results)  # At least some fills
        assert not all(results)  # Not all fill

    def test_fill_price_slippage(self):
        m = ThreeTierFillModel(seed=42)
        if m.can_fill(100.0, "BUY", 100):
            p = m.fill_price(100.0, "BUY", 100)
            assert p >= 100.0
        if m.can_fill(100.0, "SELL", 100):
            p = m.fill_price(100.0, "SELL", 100)
            assert p <= 100.0

    def test_participation_limit_blocks(self):
        m = ThreeTierFillModel()
        # Order size > 10% of book depth
        assert m.can_fill(100.0, "BUY", 1000, book_depth=5000) is False

    def test_stats(self):
        m = ThreeTierFillModel()
        s = m.get_stats()
        assert "tier1_prob" in s
        assert "tier2_prob" in s

    def test_seed_reproducibility(self):
        m1 = ThreeTierFillModel(seed=123)
        m2 = ThreeTierFillModel(seed=123)
        r1 = [m1.can_fill(100.0, "BUY", 100) for _ in range(20)]
        r2 = [m2.can_fill(100.0, "BUY", 100) for _ in range(20)]
        assert r1 == r2

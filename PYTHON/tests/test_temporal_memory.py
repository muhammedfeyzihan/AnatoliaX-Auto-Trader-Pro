"""
Test: manipulation/temporal_memory
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manipulation.temporal_memory import TemporalMemory


class TestTemporalMemory:
    def test_add_and_query(self, tmp_path):
        mem = TemporalMemory(memory_dir=tmp_path)
        mem.add_seed("usd_try_38", "USD/TRY 38 asti", importance=0.9, tags=["macro"], symbols=["THYAO"])
        context = mem.query_context("THYAO", lookback_hours=24)
        assert len(context) == 1
        assert context[0]["seed_id"] == "usd_try_38"

    def test_decay_over_time(self, tmp_path):
        mem = TemporalMemory(memory_dir=tmp_path, decay_half_life_hours=1.0)
        mem.add_seed("old", "Eski haber", importance=0.9, tags=["news"], symbols=["GARAN"])
        # Query with high min_importance should filter out if decayed enough
        # Since just added, it should still pass
        context = mem.query_context("GARAN", lookback_hours=24, min_importance=0.1)
        assert len(context) == 1
        assert context[0]["decayed_importance"] <= 0.9

    def test_macro_regime(self, tmp_path):
        mem = TemporalMemory(memory_dir=tmp_path)
        mem.add_seed("b1", "BIST yukseldi guclu", importance=0.8, tags=["macro"], symbols=[])
        mem.add_seed("b2", "BIST dustu zayif", importance=0.3, tags=["macro"], symbols=[])
        regime = mem.get_macro_regime_from_seeds()
        assert regime["regime"] == "BULL"
        assert regime["confidence"] > 0.5

    def test_cleanup_old(self, tmp_path):
        mem = TemporalMemory(memory_dir=tmp_path)
        mem.add_seed("s1", "Test", importance=0.5, tags=[], symbols=["THYAO"])
        mem.cleanup_old(max_age_hours=0)
        context = mem.query_context("THYAO", lookback_hours=1)
        assert len(context) == 0

    def test_no_match(self, tmp_path):
        mem = TemporalMemory(memory_dir=tmp_path)
        mem.add_seed("s1", "Test", importance=0.5, tags=["other"], symbols=["ASELS"])
        context = mem.query_context("THYAO", lookback_hours=24)
        assert len(context) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

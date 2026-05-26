"""
test_dynamic_symbol_rotator.py — Tests for DynamicSymbolRotator (K244)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategy.dynamic_symbol_rotator import DynamicSymbolRotator, SymbolScore
from execution.manipulation_fallback import ManipulationFallbackRouter


class TestDynamicSymbolRotator:
    def test_select_best_symbol_empty(self):
        rot = DynamicSymbolRotator(bist_universe=[])
        best = rot.select_best_symbol()
        assert best is None

    def test_should_rotate_no_scores(self):
        rot = DynamicSymbolRotator(bist_universe=["THYAO"])
        should, reason = rot.should_rotate("THYAO")
        # No scores computed, so current score is None -> should rotate
        assert should is True
        assert "skoru hesaplanamadi" in reason or "manipule" in reason

    def test_register_unregister_position(self):
        rot = DynamicSymbolRotator()
        rot.register_position("THYAO", 100.0, 10)
        assert len(rot.get_active_positions()) == 1
        rot.unregister_position("THYAO")
        assert len(rot.get_active_positions()) == 0

    def test_can_open_new_position(self):
        rot = DynamicSymbolRotator(max_positions=2)
        assert rot.can_open_new_position() is True
        rot.register_position("THYAO", 100.0, 10)
        assert rot.can_open_new_position() is True
        rot.register_position("GARAN", 50.0, 20)
        assert rot.can_open_new_position() is False

    def test_symbol_score_dataclass(self):
        sc = SymbolScore(symbol="THYAO", score=75.0, market="bist")
        assert sc.symbol == "THYAO"
        assert sc.score == 75.0
        assert sc.market == "bist"

    def test_record_rotation(self):
        rot = DynamicSymbolRotator()
        rot.record_rotation("THYAO", "GARAN", "Daha iyi skor")
        hist = rot.get_rotation_history()
        assert len(hist) == 1
        assert hist[0]["from"] == "THYAO"
        assert hist[0]["to"] == "GARAN"

    def test_get_rotation_target_no_alternatives(self):
        rot = DynamicSymbolRotator(bist_universe=[])
        target = rot.get_rotation_target("THYAO")
        assert target is not None
        assert target.original_symbol == "THYAO"

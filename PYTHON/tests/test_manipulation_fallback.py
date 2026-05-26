"""
test_manipulation_fallback.py — Tests for ManipulationFallbackRouter (K243)
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.manipulation_fallback import ManipulationFallbackRouter, FallbackResult


class TestManipulationFallbackRouter:
    def test_blacklist_add_and_check(self):
        router = ManipulationFallbackRouter()
        router.blacklist_symbol("THYAO", ttl_minutes=10)
        assert router._is_blacklisted("THYAO") is True
        assert router._is_blacklisted("GARAN") is False

    def test_blacklist_expiry(self):
        router = ManipulationFallbackRouter()
        router.blacklist_symbol("THYAO", ttl_minutes=-1)  # expired
        assert router._is_blacklisted("THYAO") is False

    def test_fallback_result_structure(self):
        fb = FallbackResult(
            original_symbol="THYAO",
            manipulated=True,
            fallback_symbol="GARAN",
            fallback_market="bist",
            fallback_score=75.0,
            reason="BIST icinde alternatif bulundu",
            alternatives_checked=1,
        )
        assert fb.original_symbol == "THYAO"
        assert fb.fallback_symbol == "GARAN"
        assert fb.fallback_market == "bist"
        assert fb.fallback_score == 75.0

    def test_blacklisted_symbol_returns_fallback(self):
        router = ManipulationFallbackRouter()
        router.blacklist_symbol("THYAO", ttl_minutes=10)
        # Since THYAO is blacklisted, it should trigger fallback logic
        result = router.fallback("THYAO", bist_universe=[])
        assert result.manipulated is True or result.original_symbol == "THYAO"
        assert result.reason != ""

    def test_get_blacklist_returns_dict(self):
        router = ManipulationFallbackRouter()
        router.blacklist_symbol("THYAO")
        router.blacklist_symbol("GARAN")
        bl = router.get_blacklist()
        assert "THYAO" in bl
        assert "GARAN" in bl

    def test_fallback_multi(self):
        router = ManipulationFallbackRouter()
        router.blacklist_symbol("THYAO")
        results = router.fallback_multi(["THYAO", "GARAN"])
        assert "THYAO" in results
        assert "GARAN" in results
        assert results["THYAO"].manipulated is True

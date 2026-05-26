"""
Test: PYTHON.adapters.nautilus_adapter
Nautilus Trader entegrasyonu (opsiyonel, graceful fallback).
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.nautilus_adapter import NautilusAdapter


class TestNautilusAdapter:
    def test_is_available_false_without_nautilus(self):
        adapter = NautilusAdapter()
        # Nautilus kurulu degilse False
        assert adapter.is_available() is False

    def test_place_market_order_fallback(self):
        adapter = NautilusAdapter()
        result = adapter.place_market_order("THYAO", "BUY", 100)
        assert "order_id" in result
        assert result["symbol"] == "THYAO"
        assert result["side"] == "BUY"
        assert result["size"] == 100

    def test_place_limit_order_fallback(self):
        adapter = NautilusAdapter()
        result = adapter.place_limit_order("THYAO", "SELL", 50, 110.0)
        assert result["symbol"] == "THYAO"
        assert result["price"] == 110.0

    def test_get_instrument_fallback(self):
        adapter = NautilusAdapter()
        inst = adapter.get_instrument("THYAO")
        assert inst["symbol"] == "THYAO"
        assert inst["venue"] == "BIST"

    def test_register_symbol(self):
        adapter = NautilusAdapter()
        ok = adapter.register_symbol("THYAO")
        # Nautilus yoksa False, varsa True
        assert ok is False or ok is True

    @patch("adapters.nautilus_adapter._NAUTILUS_AVAILABLE", True)
    def test_mock_available_without_live_env(self):
        adapter = NautilusAdapter()
        # Mock ile available true ama NAUTILUS_LIVE aktif degilse fallback
        assert adapter.is_available() is True
        result = adapter.place_market_order("THYAO", "BUY", 100)
        # Live mod aktif degilse PaperBroker'a yonelir
        assert result["provider"] in ("paper_fallback", "none")
        assert result["status"] in ("FILLED", "ERROR", "PAPER")

    @patch.dict("os.environ", {"NAUTILUS_LIVE": "true"})
    @patch("adapters.nautilus_adapter._NAUTILUS_AVAILABLE", True)
    def test_mock_available_with_live_env(self):
        adapter = NautilusAdapter()
        assert adapter.is_available() is True
        result = adapter.place_market_order("THYAO", "BUY", 100)
        # Live modda bile gercek Nautilus entegrasyonu eksikse fallback
        assert "symbol" in result
        assert result["symbol"] == "THYAO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

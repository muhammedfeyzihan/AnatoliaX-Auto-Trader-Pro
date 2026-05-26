"""
Test: PYTHON.execution.order_validator
Gecerli/gereksiz emir validasyonu.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.order_validator import OrderValidator


class TestOrderValidator:
    def test_valid_buy(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100, "sl": 95, "tp": 110})
        assert r["valid"] is True
        assert r["errors"] == []

    def test_valid_sell(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "SELL", "size": 10, "price": 100, "sl": 105, "tp": 95})
        assert r["valid"] is True

    def test_sl_above_entry_buy(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100, "sl": 105, "tp": 110})
        assert r["valid"] is False
        assert any("SL" in e for e in r["errors"])

    def test_tp_below_entry_buy(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100, "sl": 95, "tp": 90})
        assert r["valid"] is False
        assert any("TP" in e for e in r["errors"])

    def test_sl_below_entry_sell(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "SELL", "size": 10, "price": 100, "sl": 95, "tp": 110})
        assert r["valid"] is False
        assert any("SL" in e for e in r["errors"])

    def test_invalid_side(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "HOLD", "size": 10, "price": 100})
        assert r["valid"] is False

    def test_negative_size(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": -5, "price": 100})
        assert r["valid"] is False

    def test_symbol_too_short(self):
        v = OrderValidator()
        r = v.validate({"symbol": "AB", "side": "BUY", "size": 10, "price": 100})
        assert r["valid"] is False

    def test_size_over_limit(self):
        v = OrderValidator(max_size=100)
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": 200, "price": 100})
        assert r["valid"] is False

    def test_no_sl_tp(self):
        v = OrderValidator()
        r = v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100})
        assert r["valid"] is True

    def test_batch_validation(self):
        v = OrderValidator()
        orders = [
            {"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100},
            {"symbol": "GARAN", "side": "SELL", "size": -5, "price": 100},
        ]
        results = v.validate_batch(orders)
        assert results[0]["valid"] is True
        assert results[1]["valid"] is False

    def test_symbol_trimmed(self):
        v = OrderValidator()
        r = v.validate({"symbol": "  thyao  ", "side": "BUY", "size": 10, "price": 100})
        assert r["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

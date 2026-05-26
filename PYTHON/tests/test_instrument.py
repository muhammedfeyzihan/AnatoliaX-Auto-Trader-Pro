"""
Test: PYTHON.data.instrument
Instrument dataclass: tick/price formatting, validation, serialization.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.instrument import Instrument


class TestInstrument:
    def test_default_values(self):
        inst = Instrument()
        assert inst.symbol == ""
        assert inst.exchange == "BIST"
        assert inst.currency == "TRY"
        assert inst.tick_size == 0.01
        assert inst.lot_size == 1.0
        assert inst.bist100 is True

    def test_format_price_rounds_to_tick(self):
        inst = Instrument(symbol="THYAO", tick_size=0.01)
        assert inst.format_price(105.239) == 105.24
        assert inst.format_price(105.233) == 105.23

    def test_format_price_zero_tick_returns_raw(self):
        inst = Instrument(tick_size=0.0)
        assert inst.format_price(105.239) == 105.239

    def test_validate_lot_valid(self):
        inst = Instrument(lot_size=1.0)
        valid, rounded = inst.validate_lot(5.0)
        assert valid is True
        assert rounded == 5.0

    def test_validate_lot_invalid(self):
        inst = Instrument(lot_size=1.0)
        valid, rounded = inst.validate_lot(5.3)
        assert valid is False
        assert rounded == 5.0

    def test_validate_lot_zero_lot_size(self):
        inst = Instrument(lot_size=0.0)
        valid, rounded = inst.validate_lot(5.3)
        assert valid is True
        assert rounded == 5.3

    def test_to_dict(self):
        inst = Instrument(symbol="THYAO", name="Turk Hava Yollari", bist30=True)
        d = inst.to_dict()
        assert d["symbol"] == "THYAO"
        assert d["name"] == "Turk Hava Yollari"
        assert d["bist30"] is True
        assert "metadata" not in d  # metadata intentionally omitted from to_dict

    def test_bist_flags(self):
        inst = Instrument(symbol="GARAN", bist30=True, bist50=True, bist100=True)
        assert inst.bist30 is True
        assert inst.bist50 is True
        assert inst.bist100 is True

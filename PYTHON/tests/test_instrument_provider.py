"""
Test: PYTHON.data.instrument_provider
InstrumentProvider, BIST_UNIVERSE, sector/index filtering.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.instrument_provider import InstrumentProvider, BIST_UNIVERSE


class TestInstrumentProvider:
    def test_get_thyao(self):
        prov = InstrumentProvider()
        inst = prov.get("THYAO")
        assert inst.symbol == "THYAO"
        assert inst.exchange == "BIST"
        assert inst.bist30 is True
        assert inst.bist100 is True

    def test_get_garan(self):
        prov = InstrumentProvider()
        inst = prov.get("GARAN")
        assert inst.sector == "Bankacilik"
        assert inst.bist30 is True

    def test_cache(self):
        prov = InstrumentProvider()
        i1 = prov.get("THYAO")
        i2 = prov.get("THYAO")
        assert i1 is i2

    def test_filter_by_index_bist30(self):
        prov = InstrumentProvider()
        b30 = prov.filter_by_index("30")
        symbols = [i.symbol for i in b30]
        assert "THYAO" in symbols
        assert "GARAN" in symbols
        assert len(b30) == 30

    def test_filter_by_sector(self):
        prov = InstrumentProvider()
        banks = prov.filter_by_sector("Bankacilik")
        symbols = {i.symbol for i in banks}
        assert "GARAN" in symbols
        assert "AKBNK" in symbols

    def test_bist_universe_not_empty(self):
        assert len(BIST_UNIVERSE) > 0
        assert "THYAO" in BIST_UNIVERSE

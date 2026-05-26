"""
instrument_provider.py — BIST Instrument Provider + Universe.
Inspired by Nautilus Trader's InstrumentProvider.

Provides standardized Instrument definitions for all BIST stocks.
Eliminates hardcoded "THYAO" references by centralizing symbol metadata.
"""

from typing import Dict, List, Optional
from data.instrument import Instrument


# Official BIST 30 / 50 / 100 universe (representative subset)
# Users can extend this list or load from external config.
BIST_UNIVERSE: List[str] = [
    # BIST 30 (liquid large-caps)
    "THYAO", "GARAN", "ASELS", "TUPRS", "KCHOL", "BIMAS", "SAHOL",
    "EREGL", "SISE", "YKBNK", "AKBNK", "ISCTR", "HALKB", "VAKBN",
    "PETKM", "KOZAA", "KOZAL", "SASA", "ENKAI", "TOASO", "TCELL",
    "PGSUS", "KRDMD", "EKGYO", "ALARK", "CCOLA", "DOHOL", "ARCLK",
    "MGROS", "VESTL",
    # Additional BIST 50 / 100
    "ANHYT", "BERA", "BRSAN", "BTCIM", "CANTE", "CIMSA", "DESA",
    "DGNMO", "DOAS", "ECILC", "ECZYT", "ENJSA", "FROTO", "GESAN",
    "GLYHO", "GSDHO", "GUBRF", "HEKTS", "IHLGM", "INDES", "IPEKE",
    "ISGYO", "ISMEN", "KARSN", "KERVT", "KMPUR", "KONTR", "KORDS",
    "KOZAP", "LOGO", "MAVI", "NATEN", "ODAS", "OTKAR", "PARSN",
    "PEGYO", "PSGYO", "QUAGR", "REEDR", "RGYAS", "RIZFN", "SANEL",
    "SELEC", "SKBNK", "SMRTG", "SOKM", "TAVHL", "TBORG", "TEI",
    "TKFEN", "TRGYO", "TRILC", "TSKB", "TTKOM", "TTRAK", "TUKAS",
    "TURSG", "ULKER", "VKGYO", "YATAS", "YESIL", "ZOREN",
]


class InstrumentProvider:
    """
    Central registry for BIST instrument metadata.
    Provides tick_size, lot_size, sector, index membership.
    """

    # Sector mapping (representative — extend as needed)
    _SECTORS: Dict[str, str] = {
        "THYAO": "Havacilik",
        "GARAN": "Bankacilik",
        "AKBNK": "Bankacilik",
        "ISCTR": "Bankacilik",
        "HALKB": "Bankacilik",
        "VAKBN": "Bankacilik",
        "YKBNK": "Bankacilik",
        "SKBNK": "Bankacilik",
        "TSKB": "Bankacilik",
        "ASELS": "Savunma",
        "TUPRS": "Petrol",
        "PETKM": "Petrokimya",
        "KCHOL": "Holding",
        "SAHOL": "Holding",
        "DOHOL": "Holding",
        "GLYHO": "Holding",
        "GSDHO": "Holding",
        "BIMAS": "Perakende",
        "SOKM": "Perakende",
        "MGROS": "Perakende",
        "MAVI": "Perakende",
        "EREGL": "Metal",
        "KRDMD": "Metal",
        "SISE": "Cam/Seramik",
        "CIMSA": "Cimento",
        "BTCIM": "Cimento",
        "ENKAI": "Insaat",
        "ECZYT": "Ilac",
        "FROTO": "Otomotiv",
        "TOASO": "Otomotiv",
        "KARSN": "Otomotiv",
        "OTKAR": "Otomotiv",
        "TTRAK": "Otomotiv",
        "TCELL": "Telekom",
        "TTKOM": "Telekom",
        "PGSUS": "Havacilik",
        "KOZAA": "Madencilik",
        "KOZAL": "Madencilik",
        "KOZAP": "Madencilik",
        "ALARK": "Enerji",
        "ENJSA": "Enerji",
        "GESAN": "Enerji",
        "NATEN": "Enerji",
        "SASA": "Tekstil",
        "DESA": "Tekstil",
        "VESTL": "Elektronik",
        "ARCLK": "Elektronik",
        "INDES": "Elektronik",
        "LOGO": "Yazilim",
        "SMRTG": "Yazilim",
    }

    # Default tick sizes by price bracket (BIST rules)
    _TICK_SIZES: Dict[str, float] = {
        "default": 0.01,
    }

    def __init__(self, universe: Optional[List[str]] = None):
        self.universe = universe or BIST_UNIVERSE
        self._cache: Dict[str, Instrument] = {}

    def get(self, symbol: str) -> Instrument:
        """Return Instrument metadata for a symbol (cached)."""
        sym = symbol.upper()
        if sym in self._cache:
            return self._cache[sym]

        inst = self._build(sym)
        self._cache[sym] = inst
        return inst

    def _build(self, symbol: str) -> Instrument:
        sector = self._SECTORS.get(symbol, "")
        bist30 = symbol in self._bist30_set()
        bist50 = symbol in self._bist50_set()
        bist100 = symbol in self._bist100_set()

        return Instrument(
            symbol=symbol,
            name="",
            exchange="BIST",
            currency="TRY",
            tick_size=0.01,
            lot_size=1.0,
            sector=sector,
            bist30=bist30,
            bist50=bist50,
            bist100=bist100,
        )

    def _bist30_set(self) -> set:
        # First 30 symbols in BIST_UNIVERSE are BIST30 for this representative list
        return set(BIST_UNIVERSE[:30])

    def _bist50_set(self) -> set:
        # First 50 symbols
        return set(BIST_UNIVERSE[:50])

    def _bist100_set(self) -> set:
        return set(BIST_UNIVERSE)

    def list_all(self) -> List[Instrument]:
        return [self.get(s) for s in self.universe]

    def filter_by_index(self, index: str) -> List[Instrument]:
        """Filter by BIST30, BIST50, or BIST100."""
        results = []
        for sym in self.universe:
            inst = self.get(sym)
            if getattr(inst, f"bist{index}", False):
                results.append(inst)
        return results

    def filter_by_sector(self, sector: str) -> List[Instrument]:
        return [self.get(s) for s in self.universe if self.get(s).sector == sector]

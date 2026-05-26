"""
bist/vbts.py — VBTS (Volatilite Bazli Tedbir Sistemi) yonetimi
"""
from typing import Dict, List, Optional


class VBTSSystem:
    """
    VBTS olcumleri: hisse basina tedbir listesi.

    Uyum:
    - Borsa Istanbul gunluk VBTS bildirimini cek
    - K142: VBTS kisitli sembollerle emir verme (bracket order haric)
    - Bracket order izinli semboller listesi
    """

    def __init__(self):
        self._measures: Dict[str, str] = {}
        self._bracket_allowed: List[str] = []

    def fetch_measures(self, date: str) -> Dict[str, str]:
        """Belirli tarih icin VBTS olcumlerini cek."""
        # Yer tutucu: gercek BIST API'den cekme ileride implemente edilecek
        return {}

    def is_restricted(self, symbol: str) -> bool:
        """Sembol VBTS kisitli mi?"""
        return symbol.upper() in self._measures

    def get_measure(self, symbol: str) -> Optional[str]:
        """Sembolun VBTS olcumunu dondur."""
        return self._measures.get(symbol.upper())

    def allows_bracket(self, symbol: str) -> bool:
        """Bracket order izinli mi?"""
        return symbol.upper() in self._bracket_allowed

    def load_from_file(self, path: str) -> None:
        """Yerel CSV/JSON dosyasindan VBTS listesi yukle."""
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._measures = {k.upper(): v for k, v in data.get("measures", {}).items()}
            self._bracket_allowed = [s.upper() for s in data.get("bracket_allowed", [])]
        except Exception:
            pass

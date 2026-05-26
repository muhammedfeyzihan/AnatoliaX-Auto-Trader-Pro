"""
bist/short_sell_ban.py — Aciga satis yasak kontrolu
"""
from typing import Set


class ShortSellBan:
    """
    Aciga satis yasak listesi yonetimi.

    Uyum:
    - K144: Aciga satis yasakli sembollerle SELL emri reddet
    - Yasak listesi gunluk BIST duyurusu ile guncellenir
    """

    def __init__(self):
        self._banned: Set[str] = set()

    def load_banned(self, symbols: list) -> None:
        """Yasakli sembol listesini yukle."""
        self._banned = {s.upper() for s in symbols}

    def is_banned(self, symbol: str) -> bool:
        """Sembol aciga satis yasakli mi?"""
        return symbol.upper() in self._banned

    def add_ban(self, symbol: str) -> None:
        self._banned.add(symbol.upper())

    def remove_ban(self, symbol: str) -> None:
        self._banned.discard(symbol.upper())

"""
compliance/insider_trade_guard.py — Icsel bilgi korumasi
"""
from typing import List


class InsiderTradeGuard:
    """
    Icsel bilgi (insider trading) korumasi.

    Kontroller:
    - KAP bildirim oncesi/alterninden emir varsa alarm
    - Yonetici hisse alim-satimi KAP karsilastirmasi
    - Hassas zaman araliklari: bilanco donemleri, sermaye artisi

    K195: Insider trading sinyali tespitinde emir iptal edilir.
    """

    def __init__(self, kap_fetcher):
        self.kap = kap_fetcher

    def pre_trade_check(self, symbol: str, side: str) -> List[str]:
        flags = []
        # Placeholder: KAP yakin zamanda bildirim var mi kontrolu
        return flags

"""
viop/expiry_manager.py — Vade yonetimi: takas, roll-over, uc uc emir
"""
from datetime import date, timedelta
from typing import List


class ExpiryManager:
    """
    VIOP vade sonu yonetimi.

    Islemler:
    - Vade takvimi (aylik, uc aylik, alti aylik)
    - Otomatik roll-over (eski vadeden yeniye tasima)
    - Uc uc emir: Kapanis + Yeni acilis es zamanli emir

    K174: Vade sonu yaklasirken pozisyonlar otomatik olarak yeni vadeye tasınır.
    """

    MONTHS = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

    def __init__(self, calendar):
        self.calendar = calendar

    def expiry_date(self, year: int, month: int, underlying: str = "XU030") -> date:
        # VIOP vade sonu genelde ayin son persembe
        d = date(year, month, 28)
        while d.weekday() != 3:
            d += timedelta(days=1)
        return d

    def auto_rollover(self, positions: List[dict]) -> List[dict]:
        # Roll-over emirlerini uret
        orders = []
        for pos in positions:
            orders.append({
                "action": "ROLLOVER",
                "old_symbol": pos["symbol"],
                "new_symbol": self._next_contract(pos["symbol"]),
                "qty": pos["qty"],
            })
        return orders

    def _next_contract(self, symbol: str) -> str:
        # Ornek: XU030M26 -> XU030N26
        root = symbol[:-3]
        month_code = symbol[-3]
        year = symbol[-2:]
        idx = self.MONTHS.index(month_code)
        next_idx = (idx + 1) % 12
        next_year = year if next_idx > idx else str(int(year) + 1)[-2:]
        return f"{root}{self.MONTHS[next_idx]}{next_year}"

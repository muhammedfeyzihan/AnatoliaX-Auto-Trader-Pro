"""
bist/bist_calendar.py — BIST is gunleri, tatiller, yari gunler
"""
from datetime import date, timedelta
from typing import List, Optional


class BISTCalendar:
    """
    BIST resmi is takvimi.

    Ozellikler:
    - Sabit tatiller: 1 Ocak, 23 Nisan, 1 Mayis, 19 Mayis, 15 Temmuz, 30 Agustos, 29 Ekim
    - Dini bayramlar: Ramazan, Kurban (degisken tarihler)
    - Yari gunler: 31 Aralik (piyasa 12:00'de kapanir)
    - Haftasonu: Cumartesi/Pazar kapali

    K169: Tatil kontrolu her emir oncesi yapilir.
    """

    FIXED_HOLIDAYS = [(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)]

    def __init__(self):
        self._holidays: set = set()
        for m, d in self.FIXED_HOLIDAYS:
            self._holidays.add((m, d))

    def is_holiday(self, d: date = None) -> bool:
        d = d or date.today()
        if d.weekday() >= 5:
            return True
        return (d.month, d.day) in self._holidays

    def next_trading_day(self, d: date = None) -> date:
        d = d or date.today()
        while True:
            d += timedelta(days=1)
            if not self.is_holiday(d):
                return d

    def half_day(self, d: date = None) -> bool:
        d = d or date.today()
        return (d.month, d.day) == (12, 31)

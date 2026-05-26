"""
market_calendar.py — BIST resmi tatil takvimi ve piyasa acik/kapali kontrolu.
Kural: Tatil gununde islem yapilmaz. Sistem otomatik olarak kullaniciya bilgi verir.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Set


class BISTCalendar:
    """
    Borsa Istanbul resmi tatil takvimi.
    - Sabit tatiller (1 Ocak, 23 Nisan, 1 Mayis, 19 Mayis, 15 Temmuz, 30 Agustos, 29 Ekim)
    - Dini bayramlar (Ramazan + Kurban) manuel girilir cunku hicri takvime bagli.
    - Haftasonu (Cumartesi/Pazar) kapali.
    - Yari gunler (genellikle bayram arefesi) manuel tanimlanabilir.
    """

    FIXED_HOLIDAYS = {
        (1, 1),   # Yilbasi
        (4, 23),  # Ulusal Egemenlik ve Cocuk Bayrami
        (5, 1),   # Emek ve Dayanisma Gunu
        (5, 19),  # Ataturk'u Anma, Genclik ve Spor Bayrami
        (7, 15),  # Demokrasi ve Milli Birlik Gunu
        (8, 30),  # Zafer Bayrami
        (10, 29), # Cumhuriyet Bayrami
    }

    def __init__(self, religious_holidays: Optional[List[date]] = None, half_days: Optional[Set[date]] = None):
        self.religious_holidays = set(religious_holidays or [])
        self.half_days = set(half_days or [])
        self._current_year = datetime.now().year

    def is_weekend(self, dt: date) -> bool:
        return dt.weekday() >= 5  # 5=Cumartesi, 6=Pazar

    def is_fixed_holiday(self, dt: date) -> bool:
        return (dt.month, dt.day) in self.FIXED_HOLIDAYS

    def is_religious_holiday(self, dt: date) -> bool:
        return dt in self.religious_holidays

    def is_holiday(self, dt: Optional[date] = None) -> bool:
        """Tam gun tatil mi? (Haftasonu + resmi tatil + dini bayram)"""
        dt = dt or date.today()
        return self.is_weekend(dt) or self.is_fixed_holiday(dt) or self.is_religious_holiday(dt)

    def is_half_day(self, dt: Optional[date] = None) -> bool:
        """Yari gun mu? (Ogle sonrasi kapali)"""
        dt = dt or date.today()
        return dt in self.half_days

    def is_market_open(self, dt: Optional[date] = None, current_time: Optional[datetime] = None) -> bool:
        """
        Piyasa su an acik mi?
        - Tatil = kapali
        - Yari gun = 09:30-12:30 acik
        - Normal gun = 09:30-18:00 acik
        """
        dt = dt or date.today()
        current_time = current_time or datetime.now()

        if self.is_holiday(dt):
            return False

        time_only = current_time.time()
        if self.is_half_day(dt):
            return time_only >= datetime.strptime("09:30", "%H:%M").time() and time_only <= datetime.strptime("12:30", "%H:%M").time()

        return time_only >= datetime.strptime("09:30", "%H:%M").time() and time_only <= datetime.strptime("18:00", "%H:%M").time()

    def get_reason(self, dt: Optional[date] = None) -> str:
        """Kapali olma sebebini dondurur."""
        dt = dt or date.today()
        if self.is_weekend(dt):
            return "Haftasonu (BIST kapali)"
        if self.is_fixed_holiday(dt):
            return f"Resmi tatil: {dt.strftime('%d.%m.%Y')} (BIST kapali)"
        if self.is_religious_holiday(dt):
            return f"Dini bayram: {dt.strftime('%d.%m.%Y')} (BIST kapali)"
        return "Piyasa acik"

    def next_open_day(self, dt: Optional[date] = None) -> date:
        """Bir sonraki acik gunu bulur."""
        dt = dt or date.today()
        candidate = dt + timedelta(days=1)
        while self.is_holiday(candidate):
            candidate += timedelta(days=1)
        return candidate

    def set_religious_holidays(self, holidays: List[date]):
        """Dini bayramlari manuel ayarla (Hicri takvime gore degisir)."""
        self.religious_holidays = set(holidays)

    def add_half_day(self, dt: date):
        """Yari gun ekle (ornegin arefe)."""
        self.half_days.add(dt)

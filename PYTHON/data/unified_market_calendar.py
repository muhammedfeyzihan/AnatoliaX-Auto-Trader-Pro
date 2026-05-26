"""
unified_market_calendar.py — Multi-Venue Market Calendar

Tracks official holidays, trading hours, and market status for:
- BIST (Turkey stocks)
- CRYPTO (24/7 with exceptions)
- FOREX (major sessions: London, NY, Tokyo, Sydney)

Usage:
    from data.unified_market_calendar import UnifiedMarketCalendar
    cal = UnifiedMarketCalendar()
    if cal.is_market_open("BIST"):
        print("Borsa açık")
    if cal.is_market_open("CRYPTO"):
        print("Kripto açık")
    next_open = cal.next_open_time("BIST")
    session = cal.current_forex_session()
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))


@dataclass
class MarketSession:
    name: str
    start_utc: int  # hour in UTC
    end_utc: int
    active_days: Tuple[int, ...]  # 0=Mon ... 6=Sun


class UnifiedMarketCalendar:
    """
    BIST + CRYPTO + FOREX market calendar.

    Kural K250: Agentlar piyasa kapalıyken emir üretemez.
    K251: FOREX session bilgisi strateji saat filtresinde kullanılır.
    K252: Resmi tatiller otomatik yüklenir, manuel override mümkündür.
    """

    # BIST official holidays (static list for 2025-2027, auto-extensible)
    BIST_HOLIDAYS: set[str] = {
        # 2025
        "2025-01-01", "2025-04-23", "2025-05-01", "2025-05-19",
        "2025-07-09", "2025-07-30", "2025-08-01",  # Kurban Bayramı varyasyonları
        "2025-10-29",
        # 2026
        "2026-01-01", "2026-04-23", "2026-05-01", "2026-05-19",
        "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21",  # Kurban
        "2026-10-29",
        # 2027
        "2027-01-01", "2027-04-23", "2027-05-01", "2027-05-19",
        "2027-06-07", "2027-06-08", "2027-06-09", "2027-06-10", "2027-06-11",  # Kurban
        "2027-10-29",
    }

    BIST_HALF_DAYS: set[str] = {
        "2025-12-31", "2026-12-31", "2027-12-31",
    }

    BIST_HOURS = {"open_utc": 6, "close_utc": 15}  # 09:30-18:00 TR time (UTC+3)

    CRYPTO_MAINTENANCE_WINDOWS: List[Tuple[str, str]] = [
        # (start, end) UTC — major exchange maintenance
    ]

    FOREX_SESSIONS: List[MarketSession] = [
        MarketSession("Sydney", 21, 6, (0, 1, 2, 3, 4)),     # Sun 21:00 - Fri 06:00
        MarketSession("Tokyo", 0, 9, (0, 1, 2, 3, 4)),       # 00:00 - 09:00 UTC
        MarketSession("London", 7, 16, (0, 1, 2, 3, 4)),   # 07:00 - 16:00 UTC
        MarketSession("NewYork", 12, 21, (0, 1, 2, 3, 4)),  # 12:00 - 21:00 UTC
    ]

    HIGH_LIQUIDITY_OVERLAP = [
        ("London", "NewYork", 12, 16),  # London-NY overlap 12-16 UTC
    ]

    def __init__(self, extra_holidays: Optional[List[str]] = None):
        self._holidays = set(self.BIST_HOLIDAYS)
        if extra_holidays:
            self._holidays.update(extra_holidays)
        self._tz = timezone(timedelta(hours=3))  # TR time default

    # ------------------------------------------------------------------
    # BIST
    # ------------------------------------------------------------------
    def is_bist_holiday(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now(self._tz)
        return dt.strftime("%Y-%m-%d") in self._holidays

    def is_bist_half_day(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now(self._tz)
        return dt.strftime("%Y-%m-%d") in self.BIST_HALF_DAYS

    def is_bist_open(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now(self._tz)
        weekday = dt.weekday()
        if weekday >= 5:
            return False
        if self.is_bist_holiday(dt):
            return False
        hour_utc = dt.hour
        if self.is_bist_half_day(dt):
            return self.BIST_HOURS["open_utc"] <= hour_utc < self.BIST_HOURS["close_utc"] - 3
        return self.BIST_HOURS["open_utc"] <= hour_utc < self.BIST_HOURS["close_utc"]

    # ------------------------------------------------------------------
    # CRYPTO
    # ------------------------------------------------------------------
    def is_crypto_open(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now(timezone.utc)
        # Crypto is 24/7 except during known maintenance
        ts = dt.strftime("%Y-%m-%d %H:%M")
        for start, end in self.CRYPTO_MAINTENANCE_WINDOWS:
            if start <= ts <= end:
                return False
        return True

    # ------------------------------------------------------------------
    # FOREX
    # ------------------------------------------------------------------
    def current_forex_sessions(self, dt: Optional[datetime] = None) -> List[str]:
        dt = dt or datetime.now(timezone.utc)
        weekday = dt.weekday()
        hour = dt.hour
        active = []
        for sess in self.FOREX_SESSIONS:
            if weekday in sess.active_days and sess.start_utc <= hour < sess.end_utc:
                active.append(sess.name)
        return active

    def is_forex_open(self, dt: Optional[datetime] = None) -> bool:
        return len(self.current_forex_sessions(dt)) > 0

    def is_high_liquidity_overlap(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now(timezone.utc)
        weekday = dt.weekday()
        hour = dt.hour
        for s1, s2, start, end in self.HIGH_LIQUIDITY_OVERLAP:
            if weekday < 5 and start <= hour < end:
                return True
        return False

    # ------------------------------------------------------------------
    # Unified API
    # ------------------------------------------------------------------
    def is_market_open(self, venue: str = "BIST", dt: Optional[datetime] = None) -> bool:
        venue = venue.upper()
        if venue == "BIST":
            return self.is_bist_open(dt)
        if venue in ("CRYPTO", "BINANCE", "BYBIT", "OKX"):
            return self.is_crypto_open(dt)
        if venue in ("FOREX", "FX", "OANDA"):
            return self.is_forex_open(dt)
        return False

    def get_reason(self, venue: str = "BIST", dt: Optional[datetime] = None) -> str:
        dt = dt or datetime.now(self._tz)
        venue = venue.upper()
        if venue == "BIST":
            if dt.weekday() >= 5:
                return f"Haftasonu: {dt.strftime('%A')}"
            if self.is_bist_holiday(dt):
                return f"Resmi tatil: {dt.strftime('%Y-%m-%d')}"
            if self.is_bist_half_day(dt):
                if dt.hour >= self.BIST_HOURS["close_utc"] - 3:
                    return "Yarim gun: piyasa kapali"
            if not self.is_bist_open(dt):
                return "Piyasa saatleri disinda (09:30-18:00 TR)"
            return "Piyasa acik"
        if venue in ("CRYPTO", "BINANCE", "BYBIT", "OKX"):
            if not self.is_crypto_open(dt):
                return "Bakim / teknik mola"
            return "7/24 acik"
        if venue in ("FOREX", "FX"):
            sessions = self.current_forex_sessions(dt)
            if not sessions:
                return "FOREX piyasasi kapali (haftasonu)"
            return f"Aktif sessionlar: {', '.join(sessions)}"
        return "Bilinmeyen venue"

    def next_open_time(self, venue: str = "BIST", dt: Optional[datetime] = None) -> Optional[datetime]:
        dt = dt or datetime.now(self._tz)
        venue = venue.upper()
        if venue == "BIST":
            # Find next business day at 09:30 TR
            for days in range(1, 30):
                candidate = dt + timedelta(days=days)
                if candidate.weekday() < 5 and not self.is_bist_holiday(candidate):
                    return candidate.replace(hour=9, minute=30, second=0, microsecond=0)
        if venue in ("CRYPTO", "BINANCE", "BYBIT", "OKX"):
            return dt  # Always open
        if venue in ("FOREX", "FX"):
            # Next Sunday 21:00 UTC
            days_until_sunday = (6 - dt.weekday()) % 7
            if days_until_sunday == 0 and dt.hour >= 21:
                days_until_sunday = 7
            return (dt + timedelta(days=days_until_sunday)).replace(hour=21, minute=0)
        return None

    def time_until_open(self, venue: str = "BIST", dt: Optional[datetime] = None) -> Optional[timedelta]:
        nxt = self.next_open_time(venue, dt)
        if nxt is None:
            return None
        dt = dt or datetime.now(self._tz)
        return nxt - dt

    def add_holiday(self, date_str: str):
        self._holidays.add(date_str)

    def to_dict(self, venue: str = "BIST", dt: Optional[datetime] = None) -> dict:
        return {
            "venue": venue,
            "is_open": self.is_market_open(venue, dt),
            "reason": self.get_reason(venue, dt),
            "next_open": self.next_open_time(venue, dt),
            "local_time": (dt or datetime.now(self._tz)).isoformat(),
        }


if __name__ == "__main__":
    cal = UnifiedMarketCalendar()
    print("BIST acik mi:", cal.is_market_open("BIST"))
    print("CRYPTO acik mi:", cal.is_market_open("CRYPTO"))
    print("FOREX acik mi:", cal.is_market_open("FOREX"))
    print("FOREX sessions:", cal.current_forex_sessions())
    print("High liquidity overlap:", cal.is_high_liquidity_overlap())
    print("Next BIST open:", cal.next_open_time("BIST"))
    print(cal.to_dict("BIST"))

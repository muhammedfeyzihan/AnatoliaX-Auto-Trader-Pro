"""
Test: PYTHON.data.market_calendar
BIST tatil takvimi ve piyasa aciklik kontrolu.
"""
import pytest
from datetime import date, datetime, time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.market_calendar import BISTCalendar


class TestBISTCalendar:
    def test_weekend_is_holiday(self):
        cal = BISTCalendar()
        saturday = date(2026, 5, 23)  # Cumartesi
        sunday = date(2026, 5, 24)    # Pazar
        assert cal.is_holiday(saturday) is True
        assert cal.is_holiday(sunday) is True

    def test_fixed_holidays(self):
        cal = BISTCalendar()
        assert cal.is_holiday(date(2026, 1, 1)) is True   # Yilbasi
        assert cal.is_holiday(date(2026, 4, 23)) is True  # 23 Nisan
        assert cal.is_holiday(date(2026, 5, 1)) is True   # 1 Mayis
        assert cal.is_holiday(date(2026, 5, 19)) is True # 19 Mayis
        assert cal.is_holiday(date(2026, 7, 15)) is True  # 15 Temmuz
        assert cal.is_holiday(date(2026, 8, 30)) is True   # 30 Agustos
        assert cal.is_holiday(date(2026, 10, 29)) is True  # 29 Ekim

    def test_normal_day_not_holiday(self):
        cal = BISTCalendar()
        assert cal.is_holiday(date(2026, 5, 20)) is False  # Normal Sali

    def test_religious_holiday(self):
        cal = BISTCalendar(religious_holidays=[date(2026, 4, 10)])
        assert cal.is_holiday(date(2026, 4, 10)) is True

    def test_half_day(self):
        cal = BISTCalendar(half_days={date(2026, 5, 20)})
        assert cal.is_half_day(date(2026, 5, 20)) is True
        assert cal.is_holiday(date(2026, 5, 20)) is False

    def test_market_open_hours_normal(self):
        cal = BISTCalendar()
        d = date(2026, 5, 20)
        assert cal.is_market_open(d, datetime.combine(d, time(10, 0))) is True
        assert cal.is_market_open(d, datetime.combine(d, time(9, 0))) is False
        assert cal.is_market_open(d, datetime.combine(d, time(19, 0))) is False

    def test_market_open_hours_half_day(self):
        cal = BISTCalendar(half_days={date(2026, 5, 20)})
        d = date(2026, 5, 20)
        assert cal.is_market_open(d, datetime.combine(d, time(10, 0))) is True
        assert cal.is_market_open(d, datetime.combine(d, time(14, 0))) is False

    def test_market_closed_on_holiday(self):
        cal = BISTCalendar()
        d = date(2026, 1, 1)
        assert cal.is_market_open(d, datetime.combine(d, time(10, 0))) is False

    def test_reason_weekend(self):
        cal = BISTCalendar()
        assert "Haftasonu" in cal.get_reason(date(2026, 5, 23))

    def test_reason_fixed_holiday(self):
        cal = BISTCalendar()
        assert "Resmi tatil" in cal.get_reason(date(2026, 1, 1))

    def test_next_open_day(self):
        cal = BISTCalendar()
        # 1 Mayis 2026 Persembe, sonraki gun 2 Mayis Cuma = acik
        assert cal.next_open_day(date(2026, 5, 1)) == date(2026, 5, 4)

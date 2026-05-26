"""
bist/settlement.py — T+2 takas, VIOP T+1
"""
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SettlementSchedule:
    trade_date: date
    value_date: date
    settlement_type: str  # T+2 | T+1


class SettlementManager:
    """
    Takas yonetimi.

    Kurallar:
    - Pay Piyasasi: T+2 (islem gununden 2 gun sonra takas)
    - VIOP: T+1 (ertesi gun)
    - Tatil varsa: takas ertelenir

    K170: Takas gunu portfoy ve nakit bakiyesi guncellenir.
    """

    def __init__(self, calendar):
        self.calendar = calendar

    def get_value_date(self, trade_date: date, market: str = "pay") -> date:
        offset = 2 if market == "pay" else 1
        d = trade_date
        days_added = 0
        while days_added < offset:
            d += timedelta(days=1)
            if not self.calendar.is_holiday(d):
                days_added += 1
        return d

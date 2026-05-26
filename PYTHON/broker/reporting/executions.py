"""
reporting/executions.py — Islem raporlama
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List


@dataclass
class Execution:
    exec_id: str
    symbol: str
    side: str
    qty: Decimal
    price: Decimal
    commission: Decimal
    time: datetime


class ExecutionReporter:
    """
    Gunluk islem raporu uretimi.

    Raporlar:
    - Toplam hacim, komisyon, kar/zarar
    - Hisse bazli dagilim
    - Saatlik dagilim

    K180: Islem raporu gun sonu otomatik uretilir ve Telegram a gonderilir.
    """

    def __init__(self):
        self.executions: List[Execution] = []

    def add(self, exec: Execution) -> None:
        self.executions.append(exec)

    def daily_summary(self) -> dict:
        total_volume = sum(e.qty for e in self.executions)
        total_commission = sum(e.commission for e in self.executions)
        return {
            "count": len(self.executions),
            "volume": total_volume,
            "commission": total_commission,
        }

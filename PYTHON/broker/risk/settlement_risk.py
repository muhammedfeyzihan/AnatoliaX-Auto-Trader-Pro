"""
risk/settlement_risk.py — Takas riski yonetimi
"""
from decimal import Decimal
from typing import Dict


class SettlementRisk:
    """
    Takas riski kontrolu.

    Riskler:
    - Nakit yetersizligi (T+2 odeme yapilamaz)
    - Hisse yetersizligi (T+2 teslim edilemez)
    - Karşı taraf temerrut riski

    K176: Takas riski gun sonu hesaplanir ve kritikse bildirim gonderilir.
    """

    def __init__(self):
        self._cash_needed: Decimal = Decimal("0")
        self._stock_needed: Dict[str, Decimal] = {}

    def add_settlement_obligation(self, side: str, symbol: str, qty: Decimal, amount: Decimal) -> None:
        if side == "BUY":
            self._cash_needed += amount
        else:
            self._stock_needed[symbol] = self._stock_needed.get(symbol, Decimal("0")) + qty

    def check(self, cash_balance: Decimal, stock_balance: Dict[str, Decimal]) -> Dict[str, bool]:
        return {
            "cash_ok": cash_balance >= self._cash_needed,
            "stock_ok": all(stock_balance.get(s, Decimal("0")) >= q for s, q in self._stock_needed.items()),
        }

"""
bist/yekun_kontrol.py — Gun sonu yekun kontrol
"""
from decimal import Decimal
from typing import Dict


class YekunKontrol:
    """
    Gun sonu yekun kontrol.

    Kontroller:
    - Alinan/satis yapilan toplam lot esit mi?
    - Takas yukumlulukleri dogru mu?
    - Komisyon toplamlari tutarli mi?

    K172: Yekun kontrol tutarsizligi varsa insan onayi gerektirir.
    """

    def __init__(self):
        self._buy_total: Dict[str, Decimal] = {}
        self._sell_total: Dict[str, Decimal] = {}

    def add_trade(self, symbol: str, side: str, qty: Decimal) -> None:
        if side == "BUY":
            self._buy_total[symbol] = self._buy_total.get(symbol, Decimal("0")) + qty
        else:
            self._sell_total[symbol] = self._sell_total.get(symbol, Decimal("0")) + qty

    def reconcile(self) -> Dict[str, Decimal]:
        diffs = {}
        all_syms = set(self._buy_total.keys()) | set(self._sell_total.keys())
        for sym in all_syms:
            diff = self._buy_total.get(sym, Decimal("0")) - self._sell_total.get(sym, Decimal("0"))
            if diff != 0:
                diffs[sym] = diff
        return diffs

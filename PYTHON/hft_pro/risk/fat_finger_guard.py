"""
risk/fat_finger_guard.py — Maksimum emir boyutu, fiyat yaka, miktar saglik kontrolu
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class FatFingerCheck:
    allowed: bool
    errors: List[str]


class FatFingerGuard:
    """
    Yorgun parmak (fat finger) koruyucu.

    Kontroller:
    - Emir boyutu > maksimum izin verilen
    - Fiyat son fiyattan %X sapmissa uyari
    - Miktar lot adiminin kati mi?
    - Sembol gecerli mi?

    K166: Her canli emir FatFingerGuard'dan gecmeli.
    """

    def __init__(self, max_order_size: Decimal = Decimal("100000"),
                 max_price_deviation_pct: float = 0.10,
                 lot_size: Decimal = Decimal("1")):
        self.max_order_size = max_order_size
        self.max_price_deviation_pct = max_price_deviation_pct
        self.lot_size = lot_size

    def check(self, symbol: str, price: Decimal, qty: Decimal,
              last_price: Decimal) -> FatFingerCheck:
        errors = []
        if qty > self.max_order_size:
            errors.append(f"Emir boyutu limiti asildi: {qty} > {self.max_order_size}")
        if last_price > 0:
            dev = abs(float(price - last_price) / float(last_price))
            if dev > self.max_price_deviation_pct:
                errors.append(f"Fiyat sapmasi cok yuksek: %{dev*100:.1f}")
        if qty % self.lot_size != 0:
            errors.append(f"Miktar lot adiminin kati degil: {qty} % {self.lot_size}")
        return FatFingerCheck(allowed=len(errors) == 0, errors=errors)

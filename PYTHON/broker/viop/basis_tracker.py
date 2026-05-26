"""
viop/basis_tracker.py — Baz takibi: spot - vadeli farki
"""
from decimal import Decimal
from typing import Dict


class BasisTracker:
    """
    VIOP baz (basis = spot - future) takibi.

    Kullanim:
    - Kontango (basis > 0): normal durum
    - Backwardation (basis < 0): ters durum, arbitraj sinyali
    - Basis sapmasi anormal oldugunda alarm ver

    K175: Baz takibi hem arbitraj hem de risk yonetimi icin kullanilir.
    """

    def __init__(self, threshold: Decimal = Decimal("0.5")):
        self.threshold = threshold
        self._basis: Dict[str, Decimal] = {}

    def update(self, symbol: str, spot: Decimal, future: Decimal) -> None:
        self._basis[symbol] = spot - future

    def is_contango(self, symbol: str) -> bool:
        b = self._basis.get(symbol)
        return b is not None and b > 0

    def is_backwardation(self, symbol: str) -> bool:
        b = self._basis.get(symbol)
        return b is not None and b < 0

    def anomaly(self, symbol: str) -> bool:
        b = self._basis.get(symbol)
        return b is not None and abs(b) > self.threshold

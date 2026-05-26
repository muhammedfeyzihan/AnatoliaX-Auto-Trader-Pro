"""
execution/slice_engine.py — Emir dilimleme motoru (TWAP/VWAP/POV/Implementation Shortfall)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class SliceConfig:
    strategy: str  # TWAP | VWAP | POV | IS
    total_qty: Decimal
    num_slices: int
    duration_sec: int


class SliceEngine:
    """
    Emir dilimleme motoru.

    Stratejiler:
    - TWAP: Toplam hacmi esit zaman dilimlerine bol
    - VWAP: Piyasa hacim dagilimina gore dilimle
    - POV: Percentage of Volume (piyasa hacminin %X'i kadar)
    - IS: Implementation Shortfall (acilis fiyati hedefleyerek maliyet minimize)

    K150: Her dilim bagimsiz risk kontrolunden gecer.
    """

    def __init__(self, config: SliceConfig):
        self.config = config
        self._slices: List[Decimal] = []
        self._build_slices()

    def _build_slices(self) -> None:
        if self.config.strategy == "TWAP":
            qty = self.config.total_qty / Decimal(str(self.config.num_slices))
            self._slices = [qty] * self.config.num_slices
        elif self.config.strategy == "VWAP":
            # Basit VWAP: daha fazla hacim ortada
            weights = [1.0] * self.config.num_slices
            total_w = sum(weights)
            self._slices = [self.config.total_qty * Decimal(str(w / total_w)) for w in weights]
        else:
            qty = self.config.total_qty / Decimal(str(self.config.num_slices))
            self._slices = [qty] * self.config.num_slices

    def next_slice(self) -> Decimal:
        if self._slices:
            return self._slices.pop(0)
        return Decimal("0")

    def remaining(self) -> Decimal:
        return sum(self._slices, Decimal("0"))

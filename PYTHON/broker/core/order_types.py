"""
core/order_types.py — BIST'e ozel emir tipleri
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class BISTOrder:
    """
    BIST'e ozel emir tanimi.

    Ozel alanlar:
    - bist_order_type: NORMAL, KARAR, PIYASA_YAPICI, ACIK
    - vbts_flag: VBTS kisitli hisse isareti
    - short_sell_flag: Aciğa satis izni
    - viop_margin: VIOP marjin hesabi (varsa)
    """
    symbol: str
    side: str
    quantity: Decimal
    price: Optional[Decimal]
    bist_order_type: str = "NORMAL"
    vbts_flag: bool = False
    short_sell_flag: bool = False
    viop_margin: Optional[Decimal] = None

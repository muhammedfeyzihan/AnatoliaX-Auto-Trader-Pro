"""
core/order_validator.py — Emir onaylayici (on-gonderim dogrulama)
"""
from decimal import Decimal
from typing import List, Optional

from broker.core.broker_interface import Order, OrderType, TimeInForce


class OrderValidator:
    """
    Emir onaylayici: <10us hizli reddetme kontrolleri.

    Kontroller:
    - Sembol gecerli mi?
    - Fiyat adimi 0.01 TL mi?
    - Miktar pozitif mi?
    - VIOP marjin yeterli mi?
    - VBTS kisitli mi?
    - Aciga satis yasak mi?
    - Devre kesici aktif mi?
    """

    def __init__(self, circuit_breaker=None, vbts=None, short_sell_ban=None):
        self._cb = circuit_breaker
        self._vbts = vbts
        self._ssb = short_sell_ban

    def validate(self, order: Order) -> List[str]:
        """Hata mesaji listesi dondur; bos liste = gecerli."""
        errors = []
        if order.quantity <= 0:
            errors.append("Miktar sifirdan buyuk olmali.")
        if order.order_type == OrderType.LIMIT and order.price:
            if order.price % Decimal("0.01") != 0:
                errors.append("Fiyat adimi 0.01 TL olmali.")
        if self._cb and self._cb.is_triggered(order.symbol):
            errors.append("Devre kesici aktif.")
        if self._vbts and self._vbts.is_restricted(order.symbol):
            errors.append("VBTS kisitli sembol.")
        if self._ssb and order.side.value == "SELL" and self._ssb.is_banned(order.symbol):
            errors.append("Aciga satis yasakli sembol.")
        return errors

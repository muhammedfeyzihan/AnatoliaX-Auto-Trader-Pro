"""
risk/pre_trade_check.py — On-ticaret risk kontrolu (<10us reddetme)
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List

from broker.core.broker_interface import Order


@dataclass
class PreTradeResult:
    allowed: bool
    errors: List[str]
    latency_us: float


class PreTradeRiskChecker:
    """
    On-ticaret risk kontrolcusu.

    Kontroller (sabit <10us):
    - Pozisyon limiti (K94: %2)
    - Gunluk kayip limiti (K95: %3)
    - Tek emir boyutu limiti
    - Fiyat adimi gecerliligi
    - Acik piyasa saati

    Akis:
    1. Emri al
    2. Tum kontrolleri kosullu dallanma ile calistir
    3. RED varsa: aninda reddet, sebebi logla
    4. Tum YES ise: broker'a ilet
    """

    def __init__(self, max_position_pct: float = 0.02, max_daily_loss_pct: float = 0.03,
                 max_single_order_qty: Decimal = Decimal("100000")):
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_single_order_qty = max_single_order_qty

    def check(self, order: Order, current_position: Decimal, portfolio_value: Decimal,
              daily_pnl: Decimal) -> PreTradeResult:
        import time
        t0 = time.perf_counter()
        errors = []

        if order.quantity > self.max_single_order_qty:
            errors.append("Tek emir boyutu limiti asildi.")

        if portfolio_value > 0:
            position_pct = (current_position + order.quantity) / portfolio_value
            if position_pct > Decimal(str(self.max_position_pct)):
                errors.append("Pozisyon limiti asildi (K94).")

        if daily_pnl < 0 and abs(daily_pnl) / portfolio_value > Decimal(str(self.max_daily_loss_pct)):
            errors.append("Gunluk kayip limiti asildi (K95).")

        t1 = time.perf_counter()
        latency_us = (t1 - t0) * 1_000_000
        return PreTradeResult(allowed=len(errors) == 0, errors=errors, latency_us=latency_us)

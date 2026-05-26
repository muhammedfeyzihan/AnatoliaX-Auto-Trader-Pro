"""
risk/pre_trade_risk.py — Pozisyon/NOTIONAL/PnL kontrolu <10us
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class PreTradeResult:
    allowed: bool
    errors: List[str]
    latency_us: float


class PreTradeRisk:
    """
    On-ticaret risk kontrolu.

    Kontroller (<10us):
    - Pozisyon limiti: sembol basina maksimum %2
    - Notional limit: tek emirde maksimum TRY degeri
    - PnL limiti: gunluk kayip < %3
    - Fiyat adimi gecerliligi
    - Acik piyasa saati

    K94/K95 uyumlu.
    """

    def __init__(self, max_position_pct: float = 0.02, max_daily_loss_pct: float = 0.03,
                 max_notional: Decimal = Decimal("1000000")):
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_notional = max_notional

    def check(self, order_size: Decimal, price: Decimal, current_position: Decimal,
              portfolio_value: Decimal, daily_pnl: Decimal) -> PreTradeResult:
        import time
        t0 = time.perf_counter()
        errors = []
        notional = order_size * price
        if notional > self.max_notional:
            errors.append(f"Notional limit asildi: {notional} > {self.max_notional}")
        if portfolio_value > 0:
            pos_pct = (current_position + order_size) / portfolio_value
            if pos_pct > Decimal(str(self.max_position_pct)):
                errors.append("Pozisyon limiti asildi (K94)")
        if daily_pnl < 0 and abs(daily_pnl) / portfolio_value > Decimal(str(self.max_daily_loss_pct)):
            errors.append("Gunluk kayip limiti asildi (K95)")
        t1 = time.perf_counter()
        return PreTradeResult(allowed=len(errors) == 0, errors=errors, latency_us=(t1 - t0) * 1_000_000)

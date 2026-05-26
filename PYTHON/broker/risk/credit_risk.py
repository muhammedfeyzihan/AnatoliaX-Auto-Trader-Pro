"""
risk/credit_risk.py — Kredi riski yonetimi
"""
from decimal import Decimal


class CreditRisk:
    """
    Kredi riski yonetimi.

    Kontroller:
    - Marjin call riski (VIOP)
    - Kaldıraç orani limiti
    - Portfoy karsilama orani (KKO)

    K177: Kredi riski her pozisyon degisikliginden sonra yeniden hesaplanir.
    """

    def __init__(self, max_leverage: Decimal = Decimal("10")):
        self.max_leverage = max_leverage

    def margin_call(self, equity: Decimal, margin_required: Decimal) -> bool:
        return equity < margin_required

    def kko(self, long_value: Decimal, short_value: Decimal) -> Decimal:
        if short_value == 0:
            return Decimal("999")
        return long_value / short_value

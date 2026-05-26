"""
bist/emir_iletim.py — BIST emir iletim kurallari
"""
from decimal import Decimal
from typing import List


class EmirIletimKurallari:
    """
    BIST emir iletim kurallari.

    Kurallar:
    - Fiyat adimi: 0.01 TL (pay), 0.001 (VIOP)
    - Lot boyutu: 1 (pay), sozlesmeye bagli (VIOP)
    - Maksimum emir boyutu: piyasaya gore degisir
    - Emir sureleri: GUN, KIE, KE, IL, FAK, PZL

    K171: Her emir iletim kurallarina uygunlugunu dogrular.
    """

    PRICE_STEP_PAY = Decimal("0.01")
    PRICE_STEP_VIOP = Decimal("0.001")

    def validate(self, price: Decimal, qty: Decimal, market: str = "pay") -> List[str]:
        errors = []
        step = self.PRICE_STEP_PAY if market == "pay" else self.PRICE_STEP_VIOP
        if price % step != 0:
            errors.append(f"Fiyat adimi {step} olmali.")
        if qty <= 0:
            errors.append("Miktar pozitif olmali.")
        return errors

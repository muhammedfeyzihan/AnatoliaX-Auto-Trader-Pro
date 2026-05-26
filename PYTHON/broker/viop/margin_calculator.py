"""
viop/margin_calculator.py — SPAN tabanli VIOP marjin hesabi
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MarginRequirement:
    initial_margin: Decimal
    maintenance_margin: Decimal
    currency: str = "TRY"


class VIOPMarginCalculator:
    """
    VIOP marjin hesaplayici (SPAN benzeri).

    Hesaplama:
    - initial = max(senaryo1, senaryo2, senaryo3) * pozisyon_boyutu
    - maintenance = initial * 0.75
    - Para birimi: TRY (Vadeli Islemler ve Opsiyonlar Borsasi)

    K101: Her VIOP emrinden once marjin kontrolu.
    """

    def __init__(self, scenario_shocks: list = None):
        self._shocks = scenario_shocks or [0.03, 0.06, 0.09]

    def calculate(self, contract_price: Decimal, position_size: Decimal,
                  volatility: float) -> MarginRequirement:
        """Marjin gereksinimini hesapla."""
        shocks = [Decimal(str(s)) * Decimal(str(volatility)) for s in self._shocks]
        initial = max(shocks) * contract_price * position_size
        maintenance = initial * Decimal("0.75")
        return MarginRequirement(initial_margin=initial, maintenance_margin=maintenance)

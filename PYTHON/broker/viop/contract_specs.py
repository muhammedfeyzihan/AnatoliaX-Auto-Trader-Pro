"""
viop/contract_specs.py — VIOP sozlesme bilgileri ve vadeler
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class VIOPContract:
    symbol: str
    underlying: str
    expiry: str
    contract_size: Decimal
    tick_size: Decimal
    margin_initial: Decimal
    margin_maintenance: Decimal


class ContractSpecs:
    """
    VIOP sozlesme tanimlari.

    Sozlesmeler:
    - XU030: BIST 30 endeks vadeli
    - XU100: BIST 100 endeks vadeli
    - USDTRY: Dolar/TL vadeli
    - EURTRY: Euro/TL vadeli

    K173: Her VIOP emrinden once sozlesme bilgisi dogrulanir.
    """

    CONTRACTS = {
        "XU030": VIOPContract("XU030", "BIST30", "2026-06", Decimal("10"), Decimal("0.001"), Decimal("5000"), Decimal("3750")),
        "XU100": VIOPContract("XU100", "BIST100", "2026-06", Decimal("10"), Decimal("0.001"), Decimal("3000"), Decimal("2250")),
        "USDTRY": VIOPContract("USDTRY", "USD/TRY", "2026-06", Decimal("1000"), Decimal("0.0001"), Decimal("2000"), Decimal("1500")),
    }

    @classmethod
    def get(cls, symbol: str) -> VIOPContract:
        return cls.CONTRACTS.get(symbol)

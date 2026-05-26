"""
reconciliation/settlement_recon.py — Takas mutabakat
"""
from decimal import Decimal
from typing import Dict, List


class SettlementReconciliation:
    """
    Takas mutabakat motoru.

    Mutabakat:
    - Takasbank raporu ile ic sistem karsilastirma
    - Fark tespiti ve duzeltme kaydi
    - Gunluk rapor uretimi

    K178: Takas mutabakat gunluk calisir; fark varsa raporlanir.
    """

    def __init__(self):
        self.discrepancies: List[Dict] = []

    def compare(self, internal: Dict[str, Decimal], external: Dict[str, Decimal]) -> None:
        all_keys = set(internal.keys()) | set(external.keys())
        for k in all_keys:
            diff = internal.get(k, Decimal("0")) - external.get(k, Decimal("0"))
            if diff != 0:
                self.discrepancies.append({"key": k, "diff": diff})

    def report(self) -> List[Dict]:
        return self.discrepancies

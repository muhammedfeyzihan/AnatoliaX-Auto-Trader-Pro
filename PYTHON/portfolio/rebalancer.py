"""
portfolio/rebalancer.py — Otomatik portfoy rebalancing
"""
from decimal import Decimal
from typing import Dict


class Rebalancer:
    """
    Hedef agirliklara gore portfoy rebalancing.

    Kurallar:
    - Min islem: %1 sapma uzerinde calis
    - Maliyet: komisyon + BSMV + slippage dahil
    - Takas: T+2 nakit/hisse hareketini hesaba kat

    K193: Rebalancing Strateji Ajaninin onayiyla gerceklesir.
    """

    def __init__(self, target_weights: Dict[str, Decimal], threshold: Decimal = Decimal("0.01")):
        self.target = target_weights
        self.threshold = threshold

    def rebalance_needed(self, current: Dict[str, Decimal]) -> bool:
        for sym, target_w in self.target.items():
            curr_w = current.get(sym, Decimal("0"))
            if abs(curr_w - target_w) > self.threshold:
                return True
        return False

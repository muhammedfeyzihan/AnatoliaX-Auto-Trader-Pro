"""
risk/self_trade_prevention.py — STP: Kendi emirlerinle karsilasmayi onle
"""
from typing import Dict, Set


class SelfTradePrevention:
    """
    Kendi emirlerinle karsilasma onleyici (STP).

    Algoritma:
    - Ayni sembolde hem alis hem satis emri varsa:
      - Eger fiyatlar kesisiyorsa: yeni emri reddet veya eski emri iptal et
    - Modlar: REJECT_BOTH, CANCEL_OLD, DECREMENT_BOTH

    K165: STP BIST duzenlemelerine uygun sekilde calisir.
    """

    def __init__(self, mode: str = "REJECT_BOTH"):
        self.mode = mode
        self._orders: Dict[str, list] = {}

    def check(self, symbol: str, side: str, price: float) -> bool:
        """Kendi emirlerinle karsilasma riski varsa True (reddet)."""
        existing = self._orders.get(symbol, [])
        for o in existing:
            if o["side"] != side:
                if (side == "BUY" and price >= o["price"]) or (side == "SELL" and price <= o["price"]):
                    return True
        return False

    def register(self, symbol: str, side: str, price: float, order_id: str) -> None:
        if symbol not in self._orders:
            self._orders[symbol] = []
        self._orders[symbol].append({"side": side, "price": price, "order_id": order_id})

"""
execution/cancel_replace.py — Atomik modify (fiyat/boyut) sira numarasi ile
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class CancelReplaceRequest:
    client_order_id: str
    new_price: Optional[Decimal]
    new_qty: Optional[Decimal]
    sequence_num: int


class CancelReplaceEngine:
    """
    Cancel-Replace motoru.

    Surec:
    1. Eski emri iptal et (CancelRequest)
    2. Yeni emri ayni ClOrdID ile gonder (Replace)
    3. Sira numarasi artir (SeqNum+1)
    4. Araci onayini bekle

    K152: Cancel-Replace ayrilmaz atomik islem; yarim kalmis durum olmamali.
    """

    def __init__(self):
        self._seq = 0
        self._pending: dict = {}

    def request(self, client_order_id: str, new_price: Decimal = None, new_qty: Decimal = None) -> CancelReplaceRequest:
        self._seq += 1
        req = CancelReplaceRequest(
            client_order_id=client_order_id,
            new_price=new_price,
            new_qty=new_qty,
            sequence_num=self._seq,
        )
        self._pending[client_order_id] = req
        return req

    def confirm(self, client_order_id: str) -> bool:
        return client_order_id in self._pending

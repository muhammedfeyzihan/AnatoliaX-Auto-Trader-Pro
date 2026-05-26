"""
protocols/itsp_adapter.py — BIST ITSP (Istanbul Trading System Protocol) adaptoru
"""
from typing import Optional


class ITSPAdapter:
    """
    BIST ITSP (Istanbul Trading System Protocol) yerel adaptoru.

    ITSP: Borsa Istanbul'un yerel elektronik islem protokolu.
    Bu adaptorer sadece yer tutucudur; tam implementasyon ileride eklenecektir.

    K168: ITSP entegrasyonu FIX Gateway'den sonra planlanmistir.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def send_order(self, payload: dict) -> dict:
        return {"status": "pending", "order_id": "ITSP-1"}

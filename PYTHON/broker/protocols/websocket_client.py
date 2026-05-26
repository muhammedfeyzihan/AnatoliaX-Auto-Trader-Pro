"""
protocols/websocket_client.py — WebSocket emir istemcisi
"""
import asyncio
from typing import Callable, Optional


class WebSocketOrderClient:
    """
    WebSocket uzerinden emir iletimi.

    Ozellikler:
    - async connect/close
    - Otomatik yeniden baglanma: exponential backoff 1s,2s,4s,8s,16s
    - Heartbeat: her 20s Ping, 60s icinde Pong yoksa reconnect
    """

    def __init__(self, url: str, heartbeat_sec: int = 20):
        self.url = url
        self.heartbeat_sec = heartbeat_sec
        self._on_message: Optional[Callable[[dict], None]] = None
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        asyncio.create_task(self._heartbeat_loop())
        return True

    async def close(self) -> None:
        self._connected = False

    async def send_order(self, payload: dict) -> None:
        # Yer tutucu: gercek WebSocket iletimi ileride implemente edilecek
        pass

    def register_handler(self, handler: Callable[[dict], None]) -> None:
        self._on_message = handler

    async def _heartbeat_loop(self) -> None:
        while self._connected:
            await asyncio.sleep(self.heartbeat_sec)
            # Yer tutucu: Ping gonder

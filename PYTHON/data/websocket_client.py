"""
websocket_client.py — Auto-Reconnect WebSocket Client (K130)
Exponential backoff + heartbeat + reconnect limit.
"""
import asyncio
import random
import time
from typing import Callable, Optional


class ReconnectingWebSocket:
    """
    WebSocket baglanti yonetimi: disconnect oldugunda otomatik reconnect.
    """

    def __init__(
        self,
        url: str,
        on_message: Callable,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        max_attempts: int = 10,
        base_delay_ms: float = 1000,
        max_delay_ms: float = 30000,
        heartbeat_interval_sec: float = 30,
        reconnect_decay: float = 2,
    ):
        self.url = url
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.reconnect_decay = reconnect_decay
        self.attempts = 0
        self.ready = False
        self._ws = None
        self._reconnect_task = None
        self._heartbeat_task = None

    async def connect(self):
        """Baglantiyi baslat."""
        await self._connect()

    async def _connect(self):
        import websockets
        try:
            self._ws = await websockets.connect(self.url)
            self.attempts = 0
            self.ready = True
            if self.on_open:
                self.on_open()
            self._start_heartbeat()
            await self._listen()
        except Exception:
            self.ready = False
            if self.on_close:
                self.on_close()
            await self._schedule_reconnect()

    async def _listen(self):
        import websockets
        try:
            async for message in self._ws:
                self.on_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.ready = False
            if self.on_close:
                self.on_close()
            await self._schedule_reconnect()

    async def _schedule_reconnect(self):
        if self.attempts >= self.max_attempts:
            return
        delay = min(self.base_delay_ms * (self.reconnect_decay ** self.attempts), self.max_delay_ms)
        self.attempts += 1
        await asyncio.sleep(delay / 1000)
        await self._connect()

    def _start_heartbeat(self):
        async def heartbeat():
            while self.ready and self._ws:
                try:
                    await self._ws.send('{"type":"ping"}')
                except Exception:
                    break
                await asyncio.sleep(self.heartbeat_interval_sec)
        asyncio.create_task(heartbeat())

    async def send(self, payload: str):
        if self.ready and self._ws:
            await self._ws.send(payload)

    async def close(self):
        self.ready = False
        if self._ws:
            await self._ws.close()

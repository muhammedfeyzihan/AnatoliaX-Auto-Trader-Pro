"""
reconnect.py — WebSocket reconnect, exchange disconnect recovery, failover
"""
import asyncio
import time
import random
from typing import Callable, Optional, Dict


class WebSocketReconnectHandler:
    """
    WebSocket baglanti yonetimi: disconnect oldugunda otomatik reconnect,
    exponential backoff, failover endpoint destegi.
    """

    def __init__(
        self,
        connect_fn: Callable,
        on_message: Callable,
        on_disconnect: Optional[Callable] = None,
        endpoints: list = None,
        max_reconnect_delay: float = 30.0,
        heartbeat_interval: float = 15.0,
    ):
        self.connect_fn = connect_fn
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.endpoints = endpoints or []
        self.max_reconnect_delay = max_reconnect_delay
        self.heartbeat_interval = heartbeat_interval
        self._connected = False
        self._ws = None
        self._reconnect_attempts = 0
        self._current_endpoint_index = 0
        self._last_pong = time.time()

    async def run(self):
        while True:
            try:
                endpoint = self._get_endpoint()
                self._ws = await self.connect_fn(endpoint)
                self._connected = True
                self._reconnect_attempts = 0
                await self._listen()
            except Exception as e:
                self._connected = False
                if self.on_disconnect:
                    self.on_disconnect(e)
                await self._backoff_reconnect()

    def _get_endpoint(self) -> str:
        if not self.endpoints:
            return ""
        ep = self.endpoints[self._current_endpoint_index]
        self._current_endpoint_index = (self._current_endpoint_index + 1) % len(self.endpoints)
        return ep

    async def _listen(self):
        while self._connected:
            try:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=self.heartbeat_interval * 2)
                self._last_pong = time.time()
                self.on_message(msg)
            except asyncio.TimeoutError:
                if time.time() - self._last_pong > self.heartbeat_interval * 3:
                    raise ConnectionError("Heartbeat timeout")
            except Exception:
                break

    async def _backoff_reconnect(self):
        self._reconnect_attempts += 1
        delay = min(2 ** self._reconnect_attempts + random.uniform(0, 1), self.max_reconnect_delay)
        await asyncio.sleep(delay)

    def is_connected(self) -> bool:
        return self._connected

    async def send(self, payload: dict):
        if self._connected and self._ws:
            await self._ws.send(payload)


class FailoverManager:
    """Birden fazla broker/endpoint arasinda failover."""

    def __init__(self, adapters: Dict[str, Callable], primary: str = "matriks"):
        self.adapters = adapters
        self.primary = primary
        self.current = primary
        self._health: Dict[str, bool] = {k: True for k in adapters}

    async def execute(self, payload: dict) -> dict:
        tried = []
        for name in [self.current] + [k for k in self.adapters if k != self.current]:
            if not self._health.get(name, True):
                continue
            try:
                result = await self.adapters[name](payload)
                self.current = name
                return result
            except Exception as e:
                tried.append((name, str(e)))
                self._health[name] = False
        raise RuntimeError(f"Tum failover adimlari basarisiz: {tried}")

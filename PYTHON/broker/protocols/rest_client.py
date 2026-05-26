"""
protocols/rest_client.py — REST araci istemcisi
"""
import asyncio
from typing import Dict, Optional


class RESTBrokerClient:
    """
    Araci kurum REST API istemcisi.

    Ozellikler:
    - Rate limit: 10/saniye (varsayilan)
    - Timeout: 5s
    - Retry: 3 deneme, exponential backoff
    - Auth: Bearer token, header injection
    """

    def __init__(self, base_url: str, token: str, rate_limit: int = 10, timeout_sec: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.rate_limit = rate_limit
        self.timeout_sec = timeout_sec
        self._last_request = 0.0

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> dict:
        await self._throttle()
        # Yer tutucu: gercek HTTP GET ileride implemente edilecek
        return {}

    async def post(self, endpoint: str, payload: dict) -> dict:
        await self._throttle()
        # Yer tutucu: gercek HTTP POST ileride implemente edilecek
        return {}

    async def _throttle(self) -> None:
        import time
        now = time.time()
        interval = 1.0 / self.rate_limit
        if now - self._last_request < interval:
            await asyncio.sleep(interval - (now - self._last_request))
        self._last_request = time.time()

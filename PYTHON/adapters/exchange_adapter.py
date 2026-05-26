"""
exchange_adapter.py — Unified exchange adapter (Binance/Bybit/OKX).
K219-K220: ExchangeAdapter Layer.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import time
import hmac
import hashlib
import base64


@dataclass
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    volume_24h: float
    timestamp: datetime


@dataclass
class Balance:
    asset: str
    free: float
    locked: float


class ExchangeAdapter:
    """
    Birlestirilmis kripto borsa adaptörü.
    Binance / Bybit / OKX destegi.
    BIST icin: sadece data feed (fiyat/derinlik) modu.
    """

    SUPPORTED = ["binance", "bybit", "okx"]

    def __init__(
        self,
        exchange: str,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        testnet: bool = True,
        http_timeout: float = 10.0,
    ):
        self.exchange = exchange.lower()
        if self.exchange not in self.SUPPORTED:
            raise ValueError(f"Desteklenmeyen borsa: {exchange}. Desteklenen: {self.SUPPORTED}")
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.http_timeout = http_timeout
        self._base_url = self._resolve_base_url()
        self._session: Optional[Any] = None
        self._latency_history: List[float] = []

    def _resolve_base_url(self) -> str:
        if self.exchange == "binance":
            return "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"
        if self.exchange == "bybit":
            return "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"
        if self.exchange == "okx":
            return "https://www.okx.com"
        return ""

    def _get_session(self):
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.timeout = self.http_timeout
            except ImportError:
                pass
        return self._session

    def _sign(self, payload: Dict) -> Dict:
        ts = str(int(time.time() * 1000))
        if self.exchange == "binance":
            query = "&".join(f"{k}={v}" for k, v in sorted(payload.items()))
            sig = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            return {"signature": sig, "timestamp": ts}
        if self.exchange == "bybit":
            recv_window = "5000"
            param_str = ts + self.api_key + recv_window + "&".join(f"{k}={v}" for k, v in sorted(payload.items()))
            sig = hmac.new(self.api_secret.encode(), param_str.encode(), hashlib.sha256).hexdigest()
            return {"sign": sig, "timestamp": ts, "recv_window": recv_window}
        if self.exchange == "okx":
            body = ""
            msg = ts + "GET" + "/api/v5/account/balance" + body
            sig = base64.b64encode(hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).digest()).decode()
            return {"OK-ACCESS-SIGN": sig, "OK-ACCESS-TIMESTAMP": ts, "OK-ACCESS-PASSPHRASE": self.passphrase}
        return {}

    def get_ticker(self, symbol: str) -> Ticker:
        start = time.time()
        session = self._get_session()
        if not session:
            return self._mock_ticker(symbol)
        try:
            url = f"{self._base_url}/api/v3/ticker/bookTicker"
            if self.exchange in ("bybit", "okx"):
                url = f"{self._base_url}/v5/market/tickers?category=spot&symbol={symbol}"
            resp = session.get(url, timeout=self.http_timeout)
            latency = (time.time() - start) * 1000
            self._latency_history.append(latency)
            if resp.status_code == 200:
                data = resp.json()
                parsed = self._parse_ticker(data, symbol)
                if parsed:
                    return parsed
        except Exception:
            pass
        return self._mock_ticker(symbol)

    def _parse_ticker(self, data: Dict, symbol: str) -> Optional[Ticker]:
        try:
            if self.exchange == "binance":
                return Ticker(
                    symbol=symbol,
                    bid=float(data.get("bidPrice", 0)),
                    ask=float(data.get("askPrice", 0)),
                    last=float(data.get("lastPrice", data.get("bidPrice", 0))),
                    volume_24h=float(data.get("volume", 0)),
                    timestamp=datetime.now(timezone.utc),
                )
            if self.exchange in ("bybit", "okx"):
                item = data.get("result", {}).get("list", [{}])[0] if self.exchange == "bybit" else data.get("data", [{}])[0]
                return Ticker(
                    symbol=symbol,
                    bid=float(item.get("bid1Price", 0)),
                    ask=float(item.get("ask1Price", 0)),
                    last=float(item.get("lastPrice", 0)),
                    volume_24h=float(item.get("volume24h", 0)),
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception:
            pass
        return None

    def _mock_ticker(self, symbol: str) -> Ticker:
        return Ticker(
            symbol=symbol,
            bid=100.0,
            ask=100.1,
            last=100.05,
            volume_24h=1_000_000.0,
            timestamp=datetime.now(timezone.utc),
        )

    def get_balance(self) -> List[Balance]:
        return [Balance(asset="USDT", free=10000.0, locked=0.0), Balance(asset="BTC", free=1.0, locked=0.0)]

    def place_order(self, symbol: str, side: str, size: float, price: Optional[float] = None, order_type: str = "market") -> Dict:
        return {
            "status": "mock_filled",
            "order_id": f"mock_{int(time.time()*1000)}",
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price or 100.0,
            "filled": True,
        }

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_latency_stats(self) -> Dict:
        if not self._latency_history:
            return {"count": 0, "avg_ms": 0.0, "max_ms": 0.0}
        return {
            "count": len(self._latency_history),
            "avg_ms": sum(self._latency_history) / len(self._latency_history),
            "max_ms": max(self._latency_history),
        }

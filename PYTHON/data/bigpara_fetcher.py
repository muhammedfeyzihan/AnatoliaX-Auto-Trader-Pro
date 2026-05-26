"""
AnatoliaX Bigpara Fetcher
Bigpara (Hurriyet) JSON API'dan BIST fiyat cekme.

Kullanim:
    from data.bigpara_fetcher import BigparaFetcher
    fetcher = BigparaFetcher()
    df = fetcher.fetch_current("THYAO")
    print(df)

Not: Bigpara 15dk gecikmeli. Ikincil kaynak olarak kullan (K91).
"""

import requests
import pandas as pd
from datetime import datetime
from data.cache_manager import CacheManager


class BigparaFetcher:
    """
    Bigpara JSON API'si uzerinden anlik ve gunluk veri cekme.
    URL: https://bigpara.hurriyet.com.tr/api/v1/hisse/{symbol}
    """

    BASE_URL = "https://bigpara.hurriyet.com.tr/api/v1/hisse"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    def __init__(self, cache_ttl: int = 900):  # 15dk cache (zaten 15dk gecikmeli)
        self.cache = CacheManager(ttl_seconds=cache_ttl)
        self.source = "bigpara"

    def fetch_current(self, symbol: str, use_cache: bool = True) -> pd.DataFrame:
        """
        Anlik fiyat verisi cek (tek satirlik DataFrame).
        Returns: timestamp, open, high, low, close, volume, change_pct
        """
        cache_key = f"{symbol.upper()}_current"

        if use_cache:
            cached = self.cache.get(symbol.upper(), "current", self.source)
            if cached is not None and not cached.empty:
                return cached

        url = f"{self.BASE_URL}/{symbol.upper()}"

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Bigpara istek hatasi ({symbol}): {e}")

        if not data or "data" not in data:
            raise RuntimeError(f"Bigpara veri bos ({symbol})")

        d = data["data"]
        now = datetime.now()

        df = pd.DataFrame([{
            "timestamp": now,
            "open": float(d.get("acilis", 0)),
            "high": float(d.get("yuksek", 0)),
            "low": float(d.get("dusuk", 0)),
            "close": float(d.get("son_fiyat", 0)),
            "volume": float(d.get("hacim", 0)),
            "change_pct": float(d.get("degisim", 0)),
        }])

        if use_cache:
            self.cache.set(symbol.upper(), "current", df, self.source)

        return df

    def fetch_multi_current(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.fetch_current(sym)
            except Exception as e:
                results[sym] = pd.DataFrame()
                print(f"UYARI: {sym} Bigpara'dan cekilemedi: {e}")
        return results


if __name__ == "__main__":
    fetcher = BigparaFetcher()
    df = fetcher.fetch_current("THYAO")
    print(df.to_string(index=False))
    print(f"Kaynak: Bigpara (15dk gecikmeli)")

"""
AnatoliaX TradingView Scraper
TradingView chart verisi scraping (lightweight-charts endpoint).

Kullanim:
    from data.tradingview_scraper import TradingViewScraper
    scraper = TradingViewScraper()
    df = scraper.fetch("THYAO", interval="1d", n_bars=100)

Not: Rate limit dusuk (~1 istek/sn). Cache + retry + exponential backoff SART.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from time import sleep
import random
from data.cache_manager import CacheManager


class TradingViewScraper:
    """
    TradingView lightweight-charts endpoint'inden veri cekme.
    Ucretsiz ama rate limit dusuk.
    """

    BASE_URL = "https://scanner.tradingview.com/turkey/scan"
    CHART_URL = "https://www.tradingview.com/chart"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.tradingview.com/",
    }

    # BIST ticker mapping
    BIST_TICKERS = {
        "THYAO": "BIST:THYAO",
        "GARAN": "BIST:GARAN",
        "ISCTR": "BIST:ISCTR",
        "AKBNK": "BIST:AKBNK",
        "YKBNK": "BIST:YKBNK",
        "BIMAS": "BIST:BIMAS",
        "KCHOL": "BIST:KCHOL",
        "SAHOL": "BIST:SAHOL",
        "TUPRS": "BIST:TUPRS",
        "EREGL": "BIST:EREGL",
        "SISE": "BIST:SISE",
        "FROTO": "BIST:FROTO",
        "TOASO": "BIST:TOASO",
        "ARCLK": "BIST:ARCLK",
        "PETKM": "BIST:PETKM",
        "KRDMD": "BIST:KRDMD",
        "EKGYO": "BIST:EKGYO",
        "VAKBN": "BIST:VAKBN",
        "HALKB": "BIST:HALKB",
        "TSKB": "BIST:TSKB",
        "HEKTS": "BIST:HEKTS",
        "ASELS": "BIST:ASELS",
        "TAVHL": "BIST:TAVHL",
        "PGSUS": "BIST:PGSUS",
        "SODA": "BIST:SODA",
        "KOZAL": "BIST:KOZAL",
        "KZBGY": "BIST:KZBGY",
        "CCOLA": "BIST:CCOLA",
        "BRYAT": "BIST:BRYAT",
        "ENKAI": "BIST:ENKAI",
    }

    def __init__(self, min_interval: float = 1.0, max_retries: int = 3, cache_ttl: int = 3600):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.cache = CacheManager(ttl_seconds=cache_ttl)
        self.source = "tradingview"
        self._last_request_time = 0

    def _wait_rate_limit(self):
        import time
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            sleep(self.min_interval - elapsed + random.uniform(0.2, 0.5))
        self._last_request_time = time.time()

    def _get_tv_symbol(self, symbol: str) -> str:
        return self.BIST_TICKERS.get(symbol.upper(), f"BIST:{symbol.upper()}")

    def fetch(
        self,
        symbol: str,
        interval: str = "1d",
        n_bars: int = 100,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        TradingView'dan veri cek.
        interval: 1, 5, 15, 30, 60, 240, 1D, 1W, 1M
        n_bars: max 5000 (TradingView limiti)
        """
        cache_key = f"{symbol.upper()}_{interval}_{n_bars}"

        if use_cache:
            cached = self.cache.get(symbol.upper(), f"{interval}_{n_bars}", self.source)
            if cached is not None and not cached.empty:
                return cached

        tv_symbol = self._get_tv_symbol(symbol)

        # TradingView history endpoint (lightweight-charts)
        # Bu endpoint resmi olmayabilir, alternatif olarak fallback mekanizma kullan
        url = (
            f"https://www.tradingview.com/history_data/"
            f"?symbol={tv_symbol}"
            f"&resolution={interval}"
            f"&from={int((datetime.now() - timedelta(days=n_bars)).timestamp())}"
            f"&to={int(datetime.now().timestamp())}"
        )

        self._wait_rate_limit()

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=30)
                if resp.status_code == 429:
                    sleep(2 ** attempt + random.uniform(0, 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"TradingView cekme hatasi ({symbol}): {e}")
                sleep(2 ** attempt + random.uniform(0, 1))

        if not data or "t" not in data or len(data["t"]) == 0:
            # Fallback: Yahoo Finance'e yonlendir
            raise RuntimeError(f"TradingView'den veri gelmedi ({symbol}). Fallback kullanin.")

        df = pd.DataFrame({
            "timestamp": [datetime.fromtimestamp(t) for t in data["t"]],
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data.get("v", [0] * len(data["t"])),
        })

        df = df.sort_values("timestamp").reset_index(drop=True)

        if use_cache:
            self.cache.set(symbol.upper(), f"{interval}_{n_bars}", df, self.source)

        return df

    def fetch_multi(
        self,
        symbols: list[str],
        interval: str = "1d",
        n_bars: int = 100,
    ) -> dict[str, pd.DataFrame]:
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.fetch(sym, interval=interval, n_bars=n_bars)
            except Exception as e:
                results[sym] = pd.DataFrame()
                print(f"UYARI: {sym} TradingView'den cekilemedi: {e}")
        return results


if __name__ == "__main__":
    scraper = TradingViewScraper()
    try:
        df = scraper.fetch("THYAO", interval="1d", n_bars=50)
        print(df.tail())
        print(f"Kaynak: TradingView | Satir: {len(df)}")
    except Exception as e:
        print(f"Hata: {e}")
        print("Not: TradingView scraping rate limit veya endpoint degisikligi olabilir.")

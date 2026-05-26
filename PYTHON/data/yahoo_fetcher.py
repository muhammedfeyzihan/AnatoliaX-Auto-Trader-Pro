"""
AnatoliaX Yahoo Finance Fetcher
BIST hisseleri icin yfinance kullanarak ucretsiz veri cekme.

Kullanim:
    from data.yahoo_fetcher import YahooFetcher
    fetcher = YahooFetcher()
    df = fetcher.fetch("THYAO.IS", period="6mo", interval="1d")
    print(df.tail())

Not: Yahoo Finance rate limit ~2000 istek/saat. Cache ile kullan.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from data.cache_manager import CacheManager


class YahooFetcher:
    """
    Yahoo Finance uzerinden BIST hisse verisi cekme.
    BIST ticker formati: THYAO.IS, GARAN.IS, vb.
    """

    def __init__(self, cache_ttl: int = 3600):
        self.cache = CacheManager(ttl_seconds=cache_ttl)
        self.source = "yahoo"

    def fetch(
        self,
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Belirtilen sembol icin veri cek.

        Args:
            symbol: BIST ticker (ornek: "THYAO.IS"). Eger .IS yoksa otomatik ekler.
            period: Veri araligi (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Mum araligi (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            use_cache: True ise once cache bak.

        Returns:
            DataFrame: timestamp, open, high, low, close, volume
        """
        # BIST ticker kontrolu
        if ".IS" not in symbol.upper():
            ticker = f"{symbol.upper()}.IS"
        else:
            ticker = symbol.upper()

        cache_key = f"{ticker}_{period}_{interval}"

        if use_cache:
            cached = self.cache.get(ticker, f"{period}_{interval}", self.source)
            if cached is not None and not cached.empty:
                return cached

        try:
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(period=period, interval=interval)

            if df.empty:
                raise ValueError(f"Yahoo Finance'den veri gelmedi: {ticker}")

            df = df.reset_index()
            # Kolon isimlerini standartlastir
            df = df.rename(
                columns={
                    "Date": "timestamp",
                    "Datetime": "timestamp",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )

            # timestamp datetime yap
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Cache'e kaydet
            if use_cache:
                self.cache.set(ticker, f"{period}_{interval}", df, self.source)

            return df

        except Exception as e:
            raise RuntimeError(f"Yahoo Finance cekme hatasi ({ticker}): {e}")

    def fetch_multi(
        self,
        symbols: list[str],
        period: str = "6mo",
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Birden fazla sembol icin veri cek.
        Returns: {symbol: DataFrame}
        """
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.fetch(sym, period=period, interval=interval)
            except Exception as e:
                results[sym] = pd.DataFrame()
                print(f"UYARI: {sym} cekilemedi: {e}")
        return results


if __name__ == "__main__":
    fetcher = YahooFetcher()
    df = fetcher.fetch("THYAO.IS", period="1mo", interval="1d")
    print(df.tail())
    print(f"Kaynak: Yahoo Finance | Satir: {len(df)}")

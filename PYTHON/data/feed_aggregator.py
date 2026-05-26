"""
AnatoliaX Feed Aggregator
Tum ucretsiz veri kaynaklarini birlestiren merkezi modul.

Kullanim:
    from data.feed_aggregator import FeedAggregator
    agg = FeedAggregator()
    df = agg.fetch("THYAO", interval="1d", period="6mo")
    print(df)

Strateji:
    1. Birincil: Yahoo Finance (en guvenilir, ucretsiz)
    2. Ikincil: TradingView (BIST odakli, scraping)
    3. Ucuncul: Investing.com (yavaş scraping)
    4. Dordul: Bigpara (15dk gecikmeli, anlik)

Kalite Kontrol:
    - En az 1 kaynak basarili olmali
    - Cok kaynakli dogrulama: sapma >%5 ise uyari
    - Her veri yaninda kaynak ve zaman damgasi
"""

import os
import pandas as pd
from datetime import datetime
from typing import Literal
from concurrent.futures import ThreadPoolExecutor, as_completed

from data.yahoo_fetcher import YahooFetcher
from data.tradingview_scraper import TradingViewScraper
from data.investing_scraper import InvestingScraper
from data.bigpara_fetcher import BigparaFetcher
from data.cache_manager import CacheManager


class FeedAggregator:
    """
    Coklu ucretsiz veri kaynagi birlestirici.
    Fallback zinciri ile guvenilir veri saglar.
    """

    def __init__(
        self,
        primary: Literal["yahoo", "tradingview", "investing", "bigpara"] = "yahoo",
        fallback_chain: list[str] | None = None,
        cache_ttl: int = 3600,
    ):
        self.primary = primary
        self.fallback_chain = fallback_chain or ["yahoo", "tradingview", "investing", "bigpara"]
        self.cache = CacheManager(ttl_seconds=cache_ttl)

        self._fetchers = {
            "yahoo": YahooFetcher(cache_ttl=cache_ttl),
            "tradingview": TradingViewScraper(cache_ttl=cache_ttl),
            "investing": InvestingScraper(cache_ttl=cache_ttl),
            "bigpara": BigparaFetcher(cache_ttl=cache_ttl),
        }

    def fetch(
        self,
        symbol: str,
        interval: str = "1d",
        period: str = "6mo",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Belirtilen sembol icin veri cek.
        Birincil kaynak basarisiz olursa fallback zinciri calisir.

        Args:
            symbol: Hisse sembolu (ornek: "THYAO")
            interval: Mum araligi (1d, 1h, 15m, vb.)
            period: Veri araligi (6mo, 1y, vb.)
            use_cache: True ise once cache'e bak.

        Returns:
            DataFrame: timestamp, open, high, low, close, volume, source
        """
        # Cache kontrolu
        if use_cache:
            cache_key = f"agg_{symbol.upper()}_{interval}_{period}"
            cached = self.cache.get(symbol.upper(), f"agg_{interval}_{period}", "aggregator")
            if cached is not None and not cached.empty:
                return cached

        # Fallback zinciri
        last_error = None
        for source in self.fallback_chain:
            fetcher = self._fetchers.get(source)
            if fetcher is None:
                continue

            try:
                if source == "bigpara":
                    # Bigpara sadece anlik veri
                    df = fetcher.fetch_current(symbol, use_cache=use_cache)
                else:
                    df = fetcher.fetch(symbol, interval=interval, period=period, use_cache=use_cache)

                if not df.empty:
                    # Kaynak ekle
                    df["source"] = source
                    df["fetched_at"] = datetime.now()

                    # Cache'e kaydet
                    if use_cache:
                        self.cache.set(
                            symbol.upper(),
                            f"agg_{interval}_{period}",
                            df,
                            "aggregator",
                        )

                    return df

            except Exception as e:
                last_error = e
                print(f"UYARI: {source} basarisiz ({symbol}): {e}")
                continue

        # Tum kaynaklar basarisiz
        raise RuntimeError(
            f"Tum veri kaynaklari basarisiz ({symbol}). Son hata: {last_error}"
        )

    def fetch_multi(
        self,
        symbols: list[str],
        interval: str = "1d",
        period: str = "6mo",
        max_workers: int = 8,
    ) -> dict[str, pd.DataFrame]:
        """Birden fazla sembol icin paralel veri cek (K97)."""
        results: dict[str, pd.DataFrame] = {}
        if not symbols:
            return results
        if len(symbols) == 1:
            try:
                results[symbols[0]] = self.fetch(symbols[0], interval=interval, period=period)
            except Exception as e:
                results[symbols[0]] = pd.DataFrame()
                print(f"UYARI: {symbols[0]} aggregator basarisiz: {e}")
            return results

        # Paralel fetch with ThreadPoolExecutor
        def _fetch_one(sym: str) -> tuple[str, pd.DataFrame]:
            try:
                df = self.fetch(sym, interval=interval, period=period)
                return sym, df
            except Exception as e:
                print(f"UYARI: {sym} aggregator basarisiz: {e}")
                return sym, pd.DataFrame()

        with ThreadPoolExecutor(max_workers=min(max_workers, len(symbols))) as executor:
            futures = {executor.submit(_fetch_one, sym): sym for sym in symbols}
            for future in as_completed(futures):
                sym, df = future.result()
                results[sym] = df
        return results

    def validate_multi_source(
        self,
        symbol: str,
        interval: str = "1d",
        period: str = "6mo",
        max_deviation: float = 0.05,
    ) -> dict:
        """
        Birden fazla kaynaktan veri cek ve tutarlilik kontrolu yap.
        Returns: {source: df, deviations: dict, consistent: bool}
        """
        sources = ["yahoo", "tradingview", "investing"]
        data = {}

        for src in sources:
            try:
                fetcher = self._fetchers.get(src)
                if fetcher and src != "bigpara":
                    df = fetcher.fetch(symbol, interval=interval, period=period, use_cache=True)
                    if not df.empty:
                        data[src] = df
            except Exception:
                continue

        if len(data) < 2:
            return {"data": data, "deviations": {}, "consistent": True, "warning": "Yeterli kaynak yok"}

        # Son kapanis fiyatlarini karsilastir
        closes = {src: df["close"].iloc[-1] for src, df in data.items()}
        base = closes.get("yahoo", list(closes.values())[0])

        deviations = {}
        for src, price in closes.items():
            if base > 0:
                deviations[src] = abs(price - base) / base

        max_dev = max(deviations.values()) if deviations else 0
        consistent = max_dev <= max_deviation

        return {
            "data": data,
            "deviations": deviations,
            "consistent": consistent,
            "max_deviation": max_dev,
            "warning": None if consistent else f"Kaynaklar arasi sapma %{max_dev*100:.2f} (limit %{max_deviation*100})",
        }


if __name__ == "__main__":
    agg = FeedAggregator()
    df = agg.fetch("THYAO", interval="1d", period="1mo")
    print(df.tail())
    print(f"Kaynak: {df['source'].iloc[-1]} | Cekilme: {df['fetched_at'].iloc[-1]}")

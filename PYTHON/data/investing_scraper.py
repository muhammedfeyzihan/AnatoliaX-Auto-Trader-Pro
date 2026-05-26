"""
AnatoliaX Investing.com Scraper
Ucretsiz scraping ile Investing.com'dan BIST verisi cekme.

Kullanim:
    from data.investing_scraper import InvestingScraper
    scraper = InvestingScraper()
    df = scraper.fetch("THYAO", interval="1d")

Not: Investing.com scraping yavastir. Rate limit: min 2 sn aralik.
Cache kullanimi SART.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
from data.cache_manager import CacheManager


class InvestingScraper:
    """
    Investing.com'dan hisse verisi scraping.
    URL formati: https://tr.investing.com/equities/turk-hava-yollari-historical-data
    """

    BASE_URL = "https://tr.investing.com/equities"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # Investing.com URL slug mappingi (BIST 30 ornekleri)
    SLUG_MAP = {
        "THYAO": "turk-hava-yollari",
        "GARAN": "garanti-bankasi",
        "ISCTR": "is-bankasi",
        "AKBNK": "akbank",
        "YKBNK": "yapi-ve-kredi-bank",
        "BIMAS": "bim-birlesik-magazalar",
        "KCHOL": "koc-holding",
        "SAHOL": "sabanci-holding",
        "TUPRS": "tupras-turkiye-petrol",
        "EREGL": "eregl-demir-celik",
        "SISE": "sisecam",
        "FROTO": "ford-oto-san",
        "TOASO": "tofas-turk-oto-fab",
        "ARCLK": "arcelik",
        "PETKM": "petkim",
        "KRDMD": "kardemir-d",
        "EKGYO": "emlak-konut-gmyo",
        "VAKBN": "vakiflar-bankasi",
        "HALKB": "halkbank",
        "TSKB": "tskb",
        "HEKTS": "hektas",
        "ASELS": "aselsan",
        "TAVHL": "tav-havalimanlari",
        "PGSUS": "pegasus-hava-tasimaciligi",
        "SODA": "soda-sanayii",
        "KOZAL": "koza-altin",
        "KZBGY": "kuzu-gyo",
        "CCOLA": "coca-cola-icecek",
        "BRYAT": "boryat",
        "ENKAI": "enka-insaat",
    }

    def __init__(self, min_interval: float = 2.0, cache_ttl: int = 3600):
        self.min_interval = min_interval  # Saniye
        self.cache = CacheManager(ttl_seconds=cache_ttl)
        self.source = "investing"
        self._last_request_time = 0

    def _wait_rate_limit(self):
        import time
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _get_slug(self, symbol: str) -> str | None:
        return self.SLUG_MAP.get(symbol.upper())

    def fetch(
        self,
        symbol: str,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Investing.com'dan veri cek.
        interval: "1d" (gunluk), "1w" (haftalik), "1m" (aylik)
        """
        cache_key = f"{symbol.upper()}_{interval}"

        if use_cache:
            cached = self.cache.get(symbol.upper(), interval, self.source)
            if cached is not None and not cached.empty:
                return cached

        slug = self._get_slug(symbol)
        if slug is None:
            raise ValueError(f"Investing.com slug bilinmiyor: {symbol}")

        url = f"{self.BASE_URL}/{slug}-historical-data"

        self._wait_rate_limit()

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Investing.com istek hatasi ({symbol}): {e}")

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"class": "freeze-column-w-1"})

        if table is None:
            raise RuntimeError(f"Investing.com tablo bulunamadi ({symbol})")

        rows = []
        for tr in table.find("tbody").find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            try:
                date_str = tds[0].text.strip()
                # Tarih formati: "18 May 2026" veya "18 Mayıs 2026"
                # Ay isimlerini normalize et
                date_str = date_str.replace("Mayıs", "May").replace("Ağustos", "Aug")
                date_str = date_str.replace("Eylül", "Sep").replace("Ekim", "Oct")
                date_str = date_str.replace("Kasım", "Nov").replace("Aralık", "Dec")
                date_str = date_str.replace("Ocak", "Jan").replace("Şubat", "Feb")
                date_str = date_str.replace("Mart", "Mar").replace("Nisan", "Apr")
                date_str = date_str.replace("Haziran", "Jun").replace("Temmuz", "Jul")

                dt = pd.to_datetime(date_str, format="%d %b %Y", errors="coerce")
                if pd.isna(dt):
                    continue

                # Fiyat formati: 1.234,56 -> 1234.56
                def parse_price(text):
                    t = text.strip().replace(".", "").replace(",", ".")
                    return float(t) if t else 0.0

                open_p = parse_price(tds[1].text)
                high_p = parse_price(tds[2].text)
                low_p = parse_price(tds[3].text)
                close_p = parse_price(tds[4].text)
                volume = parse_price(tds[5].text)

                rows.append({
                    "timestamp": dt,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "volume": volume,
                })
            except Exception:
                continue

        if not rows:
            raise RuntimeError(f"Investing.com'dan veri parse edilemedi ({symbol})")

        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").reset_index(drop=True)

        if use_cache:
            self.cache.set(symbol.upper(), interval, df, self.source)

        return df

    def fetch_multi(self, symbols: list[str], interval: str = "1d") -> dict[str, pd.DataFrame]:
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.fetch(sym, interval=interval)
            except Exception as e:
                results[sym] = pd.DataFrame()
                print(f"UYARI: {sym} Investing.com'dan cekilemedi: {e}")
        return results


if __name__ == "__main__":
    scraper = InvestingScraper()
    df = scraper.fetch("THYAO", interval="1d")
    print(df.tail())
    print(f"Kaynak: Investing.com | Satir: {len(df)}")

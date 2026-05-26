"""
news_fetcher.py — Haber ve Sosyal Medya Verisi Cekme
Elon Musk tweetleri, ekonomik haberler, sektor haberleri.

Kullanim:
    from data.news_fetcher import NewsFetcher
    fetcher = NewsFetcher()
    news = fetcher.fetch_market_news()
    tweets = fetcher.fetch_elon_tweets()
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional


class NewsFetcher:
    """
    Haber ve sosyal medya verisi cekme.
    Not: Twitter/X API ucretlidir. Alternatif: Nitter scraping veya RSS.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    def __init__(self, cache_minutes: int = 30):
        self.cache_minutes = cache_minutes
        self._news_cache: Optional[pd.DataFrame] = None
        self._news_last_fetch: Optional[datetime] = None

    def fetch_market_news(self, limit: int = 20) -> pd.DataFrame:
        """
        Piyasa haberlerini cek (placeholder — gercek API entegrasyonu gerektirir).
        Kaynaklar: Investing.com, Bloomberg, Reuters RSS.
        """
        # RSS fallback: Investing.com RSS
        try:
            url = "https://www.investing.com/rss/news_285.rss"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            # RSS parse (basit)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            items = []
            for item in root.findall(".//item")[:limit]:
                title = item.find("title")
                pub_date = item.find("pubDate")
                link = item.find("link")
                items.append({
                    "source": "investing.com",
                    "type": "market_news",
                    "title": title.text if title is not None else "",
                    "date": pub_date.text if pub_date is not None else datetime.now().isoformat(),
                    "url": link.text if link is not None else "",
                    "sentiment": "neutral",
                })
            return pd.DataFrame(items)
        except Exception:
            pass

        return pd.DataFrame(columns=["source", "type", "title", "date", "url", "sentiment"])

    def fetch_elon_tweets(self, limit: int = 5) -> pd.DataFrame:
        """
        Elon Musk tweetleri (placeholder).
        Not: Twitter API v2 ucretlidir. Alternatif: Nitter.net scraping.
        """
        try:
            # Nitter.net (Twitter mirror) scraping
            url = "https://nitter.net/elonmusk/rss"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            items = []
            for item in root.findall(".//item")[:limit]:
                title = item.find("title")
                pub_date = item.find("pubDate")
                link = item.find("link")
                items.append({
                    "source": "twitter/elonmusk",
                    "type": "tweet",
                    "title": title.text if title is not None else "",
                    "date": pub_date.text if pub_date is not None else datetime.now().isoformat(),
                    "url": link.text if link is not None else "",
                    "sentiment": self._classify_sentiment(title.text if title is not None else ""),
                })
            return pd.DataFrame(items)
        except Exception:
            pass

        return pd.DataFrame(columns=["source", "type", "title", "date", "url", "sentiment"])

    def _classify_sentiment(self, text: str) -> str:
        """Basit duygu analizi (keyword bazli)."""
        if not text:
            return "neutral"
        text_lower = text.lower()
        positive = ["buy", "al", "yukselecek", "pump", "moon", "bull", "guclu", "buyuk", "yes"]
        negative = ["sell", "sat", "dusucek", "dump", "crash", "bear", "zayif", "hayir", "no"]

        pos_count = sum(1 for p in positive if p in text_lower)
        neg_count = sum(1 for n in negative if n in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def fetch_fed_calendar(self) -> pd.DataFrame:
        """Fed toplanti takvimi.
        Gercek entegrasyon: investing.com/economic-calendar/ veya Fed resmi RSS.
        Simdilik bos DataFrame dondurur; canli kullanimda caching onerilir.
        """
        try:
            url = "https://www.investing.com/economic-calendar/"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            if resp.status_code == 200:
                # investing.com HTML scraping (basit)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser")
                rows = []
                for tr in soup.select("table.ecoCalendarTbl tr")[1:10]:
                    tds = tr.find_all("td")
                    if len(tds) >= 4:
                        rows.append({
                            "event": tds[1].get_text(strip=True),
                            "date": tds[0].get_text(strip=True),
                            "expected": tds[2].get_text(strip=True),
                            "previous": tds[3].get_text(strip=True),
                            "importance": tds[4].get_text(strip=True) if len(tds) > 4 else "medium",
                        })
                if rows:
                    return pd.DataFrame(rows)
        except Exception:
            pass
        return pd.DataFrame(columns=["event", "date", "expected", "previous", "importance"])

    def fetch_all(self) -> pd.DataFrame:
        """Tum haber kaynaklarini birlestir."""
        market = self.fetch_market_news()
        tweets = self.fetch_elon_tweets()
        return pd.concat([market, tweets], ignore_index=True)


if __name__ == "__main__":
    fetcher = NewsFetcher()
    news = fetcher.fetch_market_news(limit=5)
    print(f"Haberler: {len(news)}")
    print(news.head().to_string(index=False))

    tweets = fetcher.fetch_elon_tweets(limit=3)
    print(f"Tweets: {len(tweets)}")
    print(tweets.head().to_string(index=False))

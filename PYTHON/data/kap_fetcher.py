"""
kap_fetcher.py — KAP.gov.tr Bildirim Cekme (Python)
KAP (Kamu Aydinlatma Platformu) son bildirimleri ceker ve analiz eder.

Kullanim:
    from data.kap_fetcher import KAPFetcher
    fetcher = KAPFetcher()
    announcements = fetcher.fetch_recent(days=1)
    print(announcements)
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


class KAPFetcher:
    """
    KAP.gov.tr API'si uzerinden hisse bildirimleri cekme.
    Not: KAP resmi API'si sinirlidir. HTML scraping fallback mevcut.
    """

    BASE_URL = "https://www.kap.org.tr/tr/api/bildirimOzeti"
    WEB_URL = "https://www.kap.org.tr/tr/bildirim-sorgula"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    # Bildirim tipi kategorileri
    ANNOUNCEMENT_TYPES = {
        "TEMETDU": "Temettu",
        "SERMAYE": "Sermaye Artirimi",
        "YONETIM": "Yonetim Kurulu",
        "FINANSAL": "Finansal Tablo",
        "ESAS": "Esas Sozlesme",
        "DIGER": "Diger",
    }

    def __init__(self, cache_minutes: int = 15):
        self.cache_minutes = cache_minutes
        self._last_fetch: Optional[datetime] = None
        self._cache: Optional[pd.DataFrame] = None

    def fetch_recent(self, days: int = 1) -> pd.DataFrame:
        """
        Son N gunluk KAP bildirimlerini cek.
        Returns: DataFrame(ticker, date, title, type, url, summary)
        """
        # Cache kontrolu
        if self._cache is not None and self._last_fetch is not None:
            if datetime.now() - self._last_fetch < timedelta(minutes=self.cache_minutes):
                return self._cache.copy()

        try:
            # KAP API denemesi (resmi API varsa)
            url = f"{self.BASE_URL}?gun={days}"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            announcements = self._parse_api_response(data)
        except Exception:
            # Fallback: Web scraping (HTML parsing)
            announcements = self._fetch_via_scraping(days=days)

        df = pd.DataFrame(announcements)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date", ascending=False).reset_index(drop=True)

        self._cache = df.copy()
        self._last_fetch = datetime.now()

        return df

    def _parse_api_response(self, data: dict) -> List[dict]:
        """KAP API yanitini parse et."""
        announcements = []
        if not isinstance(data, dict):
            return announcements

        items = data.get("data", data.get("items", []))
        if not isinstance(items, list):
            return announcements

        for item in items:
            try:
                ann = {
                    "ticker": item.get("ticker", "").strip().upper(),
                    "company": item.get("company", "").strip(),
                    "date": item.get("date", ""),
                    "title": item.get("title", "").strip(),
                    "type": self._classify_type(item.get("title", "")),
                    "url": item.get("url", ""),
                    "summary": item.get("summary", "")[:500],
                }
                announcements.append(ann)
            except Exception:
                continue

        return announcements

    def _fetch_via_scraping(self, days: int = 1) -> List[dict]:
        """KAP HTML scraping fallback."""
        try:
            resp = requests.get(self.WEB_URL, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, "html.parser")
            announcements = []
            # KAP bildirim tablosu satirlari (yapi degisebilir)
            for row in soup.select("table tbody tr")[:50]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    ticker = cols[0].get_text(strip=True)
                    title = cols[1].get_text(strip=True)
                    date_text = cols[2].get_text(strip=True)
                    announcements.append({
                        "ticker": ticker,
                        "company": "",
                        "date": date_text,
                        "title": title,
                        "type": self._classify_type(title),
                        "url": "",
                        "summary": "",
                    })
            if announcements:
                return announcements
        except Exception:
            pass
        print("UYARI: KAP API erisilemedi. HTML scraping basarisiz veya yapi degisti.")
        return []

    def _classify_type(self, title: str) -> str:
        """Bildirim basligina gore tip siniflandirma."""
        title_lower = title.lower()
        keywords = {
            "TEMETDU": ["temettu", "kar payi", "temettu dagitim"],
            "SERMAYE": ["sermaye", "bedelsiz", "bedelli", "artirim"],
            "YONETIM": ["yonetim kurulu", "yönetim kurulu", "ydk"],
            "FINANSAL": ["finansal tablo", "bilanco", "gelir tablosu"],
            "ESAS": ["esas sozlesme", "ana sozlesme"],
        }

        for ann_type, words in keywords.items():
            for word in words:
                if word in title_lower:
                    return ann_type
        return "DIGER"

    def filter_by_type(self, df: pd.DataFrame, ann_type: str) -> pd.DataFrame:
        """Bildirim tipine gore filtrele."""
        return df[df["type"] == ann_type].copy()

    def filter_by_ticker(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Hisse sembolune gore filtrele."""
        return df[df["ticker"] == ticker.upper()].copy()

    def get_today_highlights(self) -> dict:
        """
        Bugunun onemli KAP bildirimlerini ozetle.
        Returns: {"total": int, "by_type": dict, "tickers": list}
        """
        df = self.fetch_recent(days=1)
        if df.empty:
            return {"total": 0, "by_type": {}, "tickers": [], "latest": None}

        by_type = df["type"].value_counts().to_dict()
        tickers = df["ticker"].unique().tolist()
        latest = df.iloc[0].to_dict() if not df.empty else None

        return {
            "total": len(df),
            "by_type": by_type,
            "tickers": tickers,
            "latest": latest,
        }


if __name__ == "__main__":
    fetcher = KAPFetcher()
    df = fetcher.fetch_recent(days=1)
    print(f"KAP Bildirimler: {len(df)} adet")
    if not df.empty:
        print(df.head(5).to_string(index=False))
    highlights = fetcher.get_today_highlights()
    print(f"Ozet: {highlights}")

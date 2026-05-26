"""
AnatoliaX Data Cache Manager
SQLite-based veri cache: Tekrar çekmeyi önle, rate limit koruma.

Kullanim:
    from data.cache_manager import CacheManager
    cache = CacheManager(ttl_seconds=3600)
    df = cache.get("THYAO", "1d")
    if df is None:
        df = fetch_from_source()
        cache.set("THYAO", "1d", df)
"""

import os
import sqlite3
import gzip
import pickle
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DB = CACHE_DIR / "cache.db"


class CacheManager:
    """
    SQLite tabanli veri cache manager.
    - Her sembol + interval + tarih kombinasyonu icin bir kayit.
    - TTL: Varsayilan 1 saat (3600 sn).
    - Binary pickle + gzip compression ile DataFrame saklanir (K97).
    - Thread-local persistent connection (K97).
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        """Thread-local persistent SQLite connection (K97)."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(CACHE_DB), check_same_thread=False)
        return self._local.conn

    def close(self):
        """Thread-local connection'lari kapat."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def _init_db(self):
        conn = sqlite3.connect(str(CACHE_DB))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS data_cache (
                key TEXT PRIMARY KEY,
                symbol TEXT,
                interval TEXT,
                source TEXT,
                created_at TEXT,
                expires_at TEXT,
                data BLOB
            )
        """)
        conn.commit()
        conn.close()

    def _make_key(self, symbol: str, interval: str, source: str = "default") -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        raw = f"{symbol}_{interval}_{source}_{today}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, symbol: str, interval: str, source: str = "default") -> pd.DataFrame | None:
        """Cache'den veri al. TTL gecmisse None doner."""
        key = self._make_key(symbol, interval, source)
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT data, expires_at FROM data_cache WHERE key = ?",
            (key,),
        )
        row = c.fetchone()

        if row is None:
            return None

        data_blob, expires_at = row
        expires = datetime.fromisoformat(expires_at)
        if datetime.now() > expires:
            return None  # TTL gecti

        try:
            # gzip decompression (K97)
            df = pickle.loads(gzip.decompress(data_blob))
            if isinstance(df, pd.DataFrame):
                return df
        except Exception:
            pass
        return None

    def set(self, symbol: str, interval: str, df: pd.DataFrame, source: str = "default") -> None:
        """DataFrame'i cache'e kaydet. gzip compression (K97)."""
        key = self._make_key(symbol, interval, source)
        now = datetime.now()
        expires = now + timedelta(seconds=self.ttl)
        # gzip compression reduces SQLite BLOB size (K97)
        blob = gzip.compress(pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL))

        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO data_cache
               (key, symbol, interval, source, created_at, expires_at, data)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (key, symbol, interval, source, now.isoformat(), expires.isoformat(), blob),
        )
        conn.commit()

    def clear(self, symbol: str | None = None) -> None:
        """Sembol bazli veya tum cache'i temizle."""
        conn = self._get_conn()
        c = conn.cursor()
        if symbol:
            c.execute("DELETE FROM data_cache WHERE symbol = ?", (symbol,))
        else:
            c.execute("DELETE FROM data_cache")
        conn.commit()

    def stats(self) -> dict:
        """Cache istatistikleri + expired row eviction (K97)."""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM data_cache")
        total, unique = c.fetchone()

        now_iso = datetime.now().isoformat()
        c.execute(
            "SELECT COUNT(*) FROM data_cache WHERE expires_at < ?",
            (now_iso,),
        )
        expired = c.fetchone()[0]

        # Evict expired rows during stats call (K97)
        if expired > 0:
            c.execute("DELETE FROM data_cache WHERE expires_at < ?", (now_iso,))
            conn.commit()

        return {"total_entries": total, "unique_symbols": unique, "expired": expired}

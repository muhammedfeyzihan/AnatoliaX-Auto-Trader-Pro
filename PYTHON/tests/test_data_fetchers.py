"""
Test: PYTHON.data.fetchers
Veri cekme modullerinin yapi dogrulamasi (mock/placeholder testler).
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.yahoo_fetcher import YahooFetcher
from data.cache_manager import CacheManager


class TestYahooFetcher:
    def test_fetch_returns_dataframe(self):
        fetcher = YahooFetcher()
        # Mock yfinance.Ticker
        mock_df = pd.DataFrame({
            "Open": [100, 101],
            "High": [102, 103],
            "Low": [99, 100],
            "Close": [101, 102],
            "Volume": [1000, 2000],
        })
        mock_df.index = pd.to_datetime(["2026-05-17", "2026-05-18"])
        mock_df.index.name = "Date"

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_df
            mock_ticker_cls.return_value = mock_ticker

            df = fetcher.fetch("THYAO.IS", period="5d", interval="1d", use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "timestamp" in df.columns
        assert "close" in df.columns

    def test_fetch_multi(self):
        fetcher = YahooFetcher()
        with patch.object(fetcher, "fetch") as mock_fetch:
            mock_fetch.return_value = pd.DataFrame({
                "timestamp": pd.to_datetime(["2026-05-18"]),
                "close": [103.0],
            })
            results = fetcher.fetch_multi(["THYAO.IS", "GARAN.IS"], period="1d", interval="1d")
        assert "THYAO.IS" in results
        assert "GARAN.IS" in results


class TestCacheManager:
    def test_cache_set_get(self):
        cache = CacheManager(ttl_seconds=60)
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        cache.set("THYAO", "1d", df, "test")
        result = cache.get("THYAO", "1d", "test")
        assert result is not None
        assert len(result) == 2

    def test_cache_expires(self):
        cache = CacheManager(ttl_seconds=0)  # Aninda expire
        df = pd.DataFrame({"a": [1]})
        cache.set("THYAO", "1d", df, "test")
        result = cache.get("THYAO", "1d", "test")
        assert result is None

    def test_cache_stats(self):
        cache = CacheManager(ttl_seconds=60)
        df = pd.DataFrame({"a": [1]})
        cache.set("THYAO", "1d", df, "test")
        stats = cache.stats()
        assert "total_entries" in stats
        assert stats["total_entries"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

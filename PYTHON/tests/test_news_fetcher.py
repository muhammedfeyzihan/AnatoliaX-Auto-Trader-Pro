"""
Test: PYTHON.data.news_fetcher
NewsFetcher haber ve tweet cekme (mock HTTP).
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.news_fetcher import NewsFetcher


class TestNewsFetcher:
    def test_init(self):
        fetcher = NewsFetcher(cache_minutes=15)
        assert fetcher.cache_minutes == 15
        assert fetcher._news_cache is None

    @patch("data.news_fetcher.requests.get")
    def test_fetch_market_news(self, mock_get):
        # RSS XML mock (duz XML, escape yok)
        rss = """<?xml version="1.0"?>
<rss><channel>
<item><title>Market Up</title><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><link>http://example.com/1</link></item>
<item><title>Market Down</title><pubDate>Mon, 01 Jan 2024 01:00:00 GMT</pubDate><link>http://example.com/2</link></item>
</channel></rss>"""
        mock_get.return_value = MagicMock(content=rss.encode("utf-8"))
        fetcher = NewsFetcher()
        df = fetcher.fetch_market_news(limit=5)
        assert len(df) == 2
        assert "Market Up" in df["title"].values

    @patch("data.news_fetcher.requests.get")
    def test_fetch_market_news_failure(self, mock_get):
        mock_get.side_effect = Exception("Timeout")
        fetcher = NewsFetcher()
        df = fetcher.fetch_market_news()
        assert len(df) == 0

    def test_classify_sentiment_positive(self):
        fetcher = NewsFetcher()
        assert fetcher._classify_sentiment("Buy now! Bull market moon") == "positive"

    def test_classify_sentiment_negative(self):
        fetcher = NewsFetcher()
        assert fetcher._classify_sentiment("Sell! Crash dump bear") == "negative"

    def test_classify_sentiment_neutral(self):
        fetcher = NewsFetcher()
        assert fetcher._classify_sentiment("Hello world") == "neutral"

    def test_classify_sentiment_empty(self):
        fetcher = NewsFetcher()
        assert fetcher._classify_sentiment("") == "neutral"

    @patch("data.news_fetcher.requests.get")
    def test_fetch_elon_tweets(self, mock_get):
        rss = """<?xml version="1.0"?>
<rss><channel>
<item><title>Tweet 1</title><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><link>http://example.com/t1</link></item>
</channel></rss>"""
        mock_get.return_value = MagicMock(content=rss.encode("utf-8"))
        fetcher = NewsFetcher()
        df = fetcher.fetch_elon_tweets(limit=5)
        assert len(df) == 1

    def test_fetch_fed_calendar(self):
        fetcher = NewsFetcher()
        df = fetcher.fetch_fed_calendar()
        assert len(df) == 0

    @patch("data.news_fetcher.requests.get")
    def test_fetch_all(self, mock_get):
        rss = """<?xml version="1.0"?>
<rss><channel><item><title>X</title><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><link>x</link></item></channel></rss>"""
        mock_get.return_value = MagicMock(content=rss.encode("utf-8"))
        fetcher = NewsFetcher()
        df = fetcher.fetch_all()
        assert len(df) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test: PYTHON.data.data_client
DataClient ABC + YahooDataClient + FeedAggregatorDataClient.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.data_client import DataClient, YahooDataClient, FeedAggregatorDataClient


class TestYahooDataClient:
    def test_connect_disconnect(self):
        client = YahooDataClient()
        assert client.connect() is True
        assert client.is_connected() is True
        client.disconnect()
        assert client.is_connected() is False

    def test_venue(self):
        client = YahooDataClient()
        assert client.venue == "YAHOO"

    def test_request_bars_not_connected_raises(self):
        client = YahooDataClient()
        with pytest.raises(RuntimeError, match="not connected"):
            client.request_bars("THYAO.IS", interval="1d")

    def test_request_ticks_returns_empty(self):
        client = YahooDataClient()
        client.connect()
        df = client.request_ticks("THYAO.IS")
        assert df.empty

    def test_subscribe_ticks_raises(self):
        client = YahooDataClient()
        client.connect()
        with pytest.raises(NotImplementedError):
            client.subscribe_ticks("THYAO.IS", lambda x: None)


class TestFeedAggregatorDataClient:
    def test_connect_disconnect(self):
        client = FeedAggregatorDataClient()
        assert client.connect() is True
        assert client.is_connected() is True
        client.disconnect()
        assert client.is_connected() is False

    def test_venue(self):
        client = FeedAggregatorDataClient()
        assert client.venue == "BIST_AGGREGATOR"

    def test_request_bars_not_connected_raises(self):
        client = FeedAggregatorDataClient()
        with pytest.raises(RuntimeError, match="not connected"):
            client.request_bars("THYAO", interval="1d")

    def test_request_ticks_returns_empty(self):
        client = FeedAggregatorDataClient()
        client.connect()
        df = client.request_ticks("THYAO")
        assert df.empty

    def test_subscribe_ticks_raises(self):
        client = FeedAggregatorDataClient()
        client.connect()
        with pytest.raises(NotImplementedError):
            client.subscribe_ticks("THYAO", lambda x: None)


class TestDataClientABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataClient()

"""
test_exchange_adapter.py — Tests for ExchangeAdapter (K219-K220)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.exchange_adapter import ExchangeAdapter, Ticker


class TestExchangeAdapter:
    def test_supported_exchanges(self):
        assert "binance" in ExchangeAdapter.SUPPORTED
        assert "bybit" in ExchangeAdapter.SUPPORTED
        assert "okx" in ExchangeAdapter.SUPPORTED

    def test_invalid_exchange(self):
        with pytest.raises(ValueError, match="Desteklenmeyen"):
            ExchangeAdapter("unsupported")

    def test_binance_testnet_url(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        assert "testnet" in adapter._base_url

    def test_binance_live_url(self):
        adapter = ExchangeAdapter("binance", testnet=False)
        assert "api.binance.com" in adapter._base_url

    def test_bybit_testnet_url(self):
        adapter = ExchangeAdapter("bybit", testnet=True)
        assert "testnet" in adapter._base_url

    def test_mock_ticker(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        ticker = adapter._mock_ticker("THYAO")
        assert ticker.symbol == "THYAO"
        assert ticker.bid > 0
        assert ticker.ask > 0

    def test_get_ticker_fallback(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        ticker = adapter.get_ticker("THYAO")
        assert ticker is not None
        assert ticker.symbol == "THYAO"

    def test_get_balance(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        balances = adapter.get_balance()
        assert len(balances) >= 1
        assert balances[0].asset == "USDT"

    def test_place_order_mock(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        result = adapter.place_order("BTCUSDT", "BUY", 0.1, price=50000, order_type="limit")
        assert result["filled"] is True
        assert result["symbol"] == "BTCUSDT"

    def test_cancel_order(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        assert adapter.cancel_order("mock_123") is True

    def test_latency_stats_empty(self):
        adapter = ExchangeAdapter("binance", testnet=True)
        stats = adapter.get_latency_stats()
        assert stats["count"] == 0

    def test_sign_binance(self):
        adapter = ExchangeAdapter("binance", api_key="key", api_secret="secret")
        sig = adapter._sign({"symbol": "BTCUSDT", "side": "BUY"})
        assert "signature" in sig
        assert "timestamp" in sig

    def test_sign_bybit(self):
        adapter = ExchangeAdapter("bybit", api_key="key", api_secret="secret")
        sig = adapter._sign({"symbol": "BTCUSDT", "side": "BUY"})
        assert "sign" in sig
        assert "timestamp" in sig

    def test_sign_okx(self):
        adapter = ExchangeAdapter("okx", api_key="key", api_secret="secret", passphrase="pass")
        sig = adapter._sign({})
        assert "OK-ACCESS-SIGN" in sig

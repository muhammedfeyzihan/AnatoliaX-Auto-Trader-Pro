"""
Test: PYTHON.data.auto_validator
AutoValidator fiyat dogrulama, batch, pozisyon monitor.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.auto_validator import AutoValidator


class TestAutoValidator:
    def test_init(self):
        av = AutoValidator()
        assert av.DEVIATION_LIMIT_PCT == 1.0

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_valid(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 100.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        result = av.validate_symbol("THYAO", expected_price=100.0)
        assert result["valid"] is True
        assert "DOGRULANDI" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_deviation(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 110.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        result = av.validate_symbol("THYAO", expected_price=100.0)
        assert result["valid"] is False
        assert "SAPMA" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_sl_hit(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 95.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        # expected_price vermeden sadece SL kontrolu test edilir
        result = av.validate_symbol("THYAO", expected_sl=96.0)
        assert result["valid"] is False
        assert "STOP" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_tp_hit(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 105.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        # expected_price vermeden sadece TP kontrolu test edilir
        result = av.validate_symbol("THYAO", expected_tp=104.0)
        assert result["valid"] is False
        assert "TP" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_empty_df(self, mock_fetch):
        mock_fetch.return_value = MagicMock(empty=True)
        av = AutoValidator()
        result = av.validate_symbol("THYAO", expected_price=100.0)
        assert result["valid"] is False
        assert "cekilemedi" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_symbol_exception(self, mock_fetch):
        mock_fetch.side_effect = Exception("Timeout")
        av = AutoValidator()
        result = av.validate_symbol("THYAO", expected_price=100.0)
        assert result["valid"] is False
        assert "HATA" in result["reason"]

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_validate_batch(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 100.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        results = av.validate_batch([
            {"symbol": "THYAO", "expected_price": 100.0},
            {"symbol": "GARAN", "expected_price": 100.0},
        ])
        assert len(results) == 2
        assert results[0]["valid"] is True

    @patch("data.auto_validator.FeedAggregator.fetch")
    def test_monitor_open_positions(self, mock_fetch):
        row = MagicMock(
            __getitem__=lambda self, k: {"close": 95.0, "source": "yahoo"}.get(k),
            get=lambda self, k, default=None: {"source": "yahoo"}.get(k, default),
        )
        mock_fetch.return_value = MagicMock(
            empty=False,
            iloc=MagicMock(__getitem__=lambda self, k: row),
        )
        av = AutoValidator()
        alarms = av.monitor_open_positions([
            {"symbol": "THYAO", "entry": 100.0, "sl": 96.0, "tp": 110.0},
        ])
        assert len(alarms) == 1
        assert alarms[0]["symbol"] == "THYAO"
        assert "STOP" in alarms[0]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

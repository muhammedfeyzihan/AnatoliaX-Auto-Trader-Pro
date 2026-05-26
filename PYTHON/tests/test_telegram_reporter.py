"""
Test: PYTHON.telegram.reporter
TelegramReporter rapor ve alarm gonderimi.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telegram.reporter import TelegramReporter


class TestTelegramReporter:
    def test_init_without_env(self):
        os.environ.pop("AX_TELEGRAM_TOKEN", None)
        os.environ.pop("AX_TELEGRAM_CHAT_ID", None)
        reporter = TelegramReporter()
        assert reporter.token == ""
        assert reporter.chat_id == ""

    def test_send_message_no_token(self):
        reporter = TelegramReporter(token="", chat_id="")
        assert reporter._send_message("test") is False

    @patch("telegram.reporter.requests.post")
    def test_send_message_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter._send_message("Merhaba")
        assert ok is True
        mock_post.assert_called_once()

    @patch("telegram.reporter.requests.post")
    def test_send_message_failure(self, mock_post):
        mock_post.return_value = MagicMock(status_code=403)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter._send_message("Merhaba")
        assert ok is False

    @patch("telegram.reporter.requests.post")
    def test_send_alert(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter.send_alert("Max DD exceeded", level="critical")
        assert ok is True
        call_args = mock_post.call_args
        assert "🚨" in call_args[1]["json"]["text"]

    @patch("telegram.reporter.requests.post")
    def test_send_signal_alert(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        signal = {
            "symbol": "THYAO",
            "score": 85.0,
            "entry": 100.0,
            "sl": 95.0,
            "tp1": 110.0,
            "tp2": 120.0,
            "r_r": 2.5,
            "kelly": 0.5,
            "executed": True,
        }
        ok = reporter.send_signal_alert(signal)
        assert ok is True
        call_args = mock_post.call_args
        assert "THYAO" in call_args[1]["json"]["text"]

    @patch("telegram.reporter.requests.post")
    @patch("telegram.reporter.PaperBroker.get_portfolio_summary")
    @patch("telegram.reporter.PaperBroker.get_open_positions")
    def test_send_midday_report(self, mock_pos, mock_summary, mock_post):
        mock_summary.return_value = {
            "cash": 50000.0,
            "total_value": 100000.0,
            "daily_pnl": 1000.0,
            "cumulative_pnl": 5000.0,
            "max_drawdown": 5.0,
            "open_positions": 0,
            "alerts": [],
        }
        mock_pos.return_value = []
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter.send_midday_report()
        assert ok is True

    @patch("telegram.reporter.requests.post")
    @patch("telegram.reporter.PaperBroker.get_portfolio_summary")
    def test_send_evening_report(self, mock_summary, mock_post):
        mock_summary.return_value = {
            "cash": 50000.0,
            "total_value": 100000.0,
            "daily_pnl": -500.0,
            "cumulative_pnl": 4500.0,
            "max_drawdown": 5.0,
            "open_positions": 0,
            "alerts": [],
        }
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter.send_evening_report()
        assert ok is True

    @patch("telegram.reporter.requests.post")
    def test_send_opening_report(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter.send_opening_report(symbols=["THYAO"])
        assert ok is True

    @patch("telegram.reporter.requests.post")
    def test_send_morning_report(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        reporter = TelegramReporter(token="fake-token", chat_id="12345")
        ok = reporter.send_morning_report()
        assert ok is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

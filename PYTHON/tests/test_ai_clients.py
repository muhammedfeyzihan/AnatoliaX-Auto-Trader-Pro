"""
Test: PYTHON.ai.ollama_client + PYTHON.ai.cloud_client
Ollama (Gemma) ve Cloud (Kimi) AI istemcileri.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.ollama_client import OllamaClient
from ai.cloud_client import CloudClient, SignalAgentAI, RiskAgentAI, StrategyAgentAI


class TestOllamaClient:
    def test_is_available_false_when_no_server(self):
        client = OllamaClient(base_url="http://localhost:59999")  # yanlis port
        assert client.is_available() is False

    def test_generate_returns_error_when_offline(self):
        client = OllamaClient(base_url="http://localhost:59999")
        result = client.generate("test", model="gemma")
        assert "error" in result
        assert result["error"] is not None

    @patch("ai.ollama_client.requests.Session.post")
    @patch("ai.ollama_client.requests.Session.get")
    def test_generate_success(self, mock_get, mock_post):
        mock_get.return_value = MagicMock(status_code=200)
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"response": "Merhaba", "done": True})
        client = OllamaClient()
        result = client.generate("test", model="gemma")
        assert result.get("response") == "Merhaba"
        assert result.get("error") is None

    @patch("ai.ollama_client.requests.Session.get")
    def test_list_models(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": [{"name": "gemma"}, {"name": "llama2"}]})
        client = OllamaClient()
        models = client.list_models()
        assert "gemma" in models


class TestStrategyAgentAI:
    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "Trend pozitif, alinabilir.", "error": None})
    def test_rationale_success(self, mock_gen):
        ai = StrategyAgentAI()
        text = ai.decision_rationale("THYAO", {"signal_score": 85, "risk_label": "UYGUN", "regime": "BULL", "kelly": 0.5, "r_r": 2.5})
        assert "pozitif" in text or "alinabilir" in text

    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "", "error": "Baglanti yok"})
    def test_rationale_error(self, mock_gen):
        ai = StrategyAgentAI()
        text = ai.decision_rationale("THYAO", {})
        assert "alamadi" in text or "Baglanti" in text


class TestCloudClient:
    def test_not_configured_without_env(self):
        # Token ortam degiskeni yok
        for key in ["AX_KIMI_API_KEY", "AX_OPENROUTER_KEY"]:
            os.environ.pop(key, None)
        client = CloudClient(provider="kimi")
        assert client.is_configured() is False

    def test_fallback_when_no_token(self):
        for key in ["AX_KIMI_API_KEY", "AX_OPENROUTER_KEY"]:
            os.environ.pop(key, None)
        client = CloudClient(provider="kimi")
        result = client.generate("test")
        assert "error" in result or "provider" in result

    @patch.dict(os.environ, {"AX_KIMI_API_KEY": "fake-key"})
    @patch("ai.cloud_client.requests.post")
    def test_cloud_call_with_token(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"choices": [{"message": {"content": "Kimi yanıtı"}}]}
        )
        client = CloudClient(provider="kimi")
        result = client.generate("test")
        assert result.get("response") == "Kimi yanıtı"
        assert result.get("provider") == "kimi"


class TestSignalAgentAI:
    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "Yukari momentum guclu.", "error": None})
    def test_analyze_commentary(self, mock_gen):
        ai = SignalAgentAI()
        text = ai.analyze_commentary("THYAO", {"score": 80, "entry": 100, "sl": 95, "tp1": 110, "r_r": 2.0, "kelly": 0.5, "regime": "BULL"})
        assert "momentum" in text or "guclu" in text

    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "", "error": "Baglanti yok"})
    def test_analyze_commentary_error(self, mock_gen):
        ai = SignalAgentAI()
        text = ai.analyze_commentary("THYAO", {})
        assert "alamadi" in text or "Baglanti" in text


class TestRiskAgentAI:
    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "Risk dengeli.", "error": None})
    def test_risk_summary(self, mock_gen):
        ai = RiskAgentAI()
        text = ai.risk_summary({"max_drawdown": 5.0, "sharpe_ratio": 1.2, "win_rate": 55, "daily_pnl": 100})
        assert "dengeli" in text or "Risk" in text

    @patch("ai.cloud_client.CloudClient.generate", return_value={"response": "", "error": "Timeout"})
    def test_risk_summary_error(self, mock_gen):
        ai = RiskAgentAI()
        text = ai.risk_summary({})
        assert "alamadi" in text or "Timeout" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

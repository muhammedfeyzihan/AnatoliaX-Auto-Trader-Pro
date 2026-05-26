"""
cloud_client.py — Bulut Model API Client (Kimi/Others)
Token SADECE ortam degiskeninden okunur, kodda asla yazilmaz.
Fallback: Ollama yerel (token yoksa).

Kullanim:
    from ai.cloud_client import CloudClient
    client = CloudClient()
    response = client.generate("Nihai karar: THYAO", provider="kimi")
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import os
import requests
from typing import Optional

from ai.ollama_client import OllamaClient


class CloudClient:
    """
    Bulut API istemcisi. Token .env veya ortam degiskeninden okunur.
    Token yoksa Ollama'ya fallback yapar (hicbir token kodda yok).
    """

    PROVIDERS = {
        "kimi": {
            "base_url": "https://api.moonshot.cn/v1",  # Kimi K2.6 placeholder
            "env_key": "AX_KIMI_API_KEY",
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "AX_OPENROUTER_KEY",
        },
    }

    def __init__(self, provider: str = "kimi"):
        self.provider = provider
        self.config = self.PROVIDERS.get(provider, self.PROVIDERS["kimi"])
        self._token: Optional[str] = None
        self._ollama_fallback = OllamaClient()

    @property
    def token(self) -> Optional[str]:
        """Tokeni ortam degiskeninden oku (cache'le)."""
        if self._token is None:
            self._token = os.getenv(self.config["env_key"], "").strip() or None
        return self._token

    def is_configured(self) -> bool:
        return self.token is not None

    def generate(self, prompt: str, model: Optional[str] = None) -> dict:
        """
        Bulut API'den yanut al. Token yoksa Ollama fallback.
        Returns: {"response": str, "provider": str, "error": str|None}
        """
        if not self.is_configured():
            return self._fallback_to_ollama(prompt)
        return self._call_cloud(prompt, model)

    def _call_cloud(self, prompt: str, model: Optional[str]) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "kimi-k2-6",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 512,
        }
        try:
            resp = requests.post(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"response": content.strip(), "provider": self.provider, "error": None}
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 401:
                return {"response": "", "provider": self.provider, "error": "API token gecersiz (401)"}
            return {"response": "", "provider": self.provider, "error": f"HTTP {resp.status_code}: {e}"}
        except Exception as e:
            return {"response": "", "provider": self.provider, "error": str(e)}

    def _fallback_to_ollama(self, prompt: str) -> dict:
        if self._ollama_fallback.is_available():
            result = self._ollama_fallback.generate(prompt, model="gemma")
            if not result.get("error"):
                return {
                    "response": result.get("response", ""),
                    "provider": "ollama_fallback",
                    "error": None,
                }
        return {
            "response": "",
            "provider": "none",
            "error": f"Cloud token ({self.config['env_key']}) tanimli degil ve Ollama calismiyor.",
        }


class SignalAgentAI:
    """
    Sinyal Ajanı için Kimi/Bulut entegrasyonu.
    Teknik analiz sonuçlarını doğal dil yorumuna çevirir.
    """

    def __init__(self, client: Optional[CloudClient] = None):
        self.client = client or CloudClient(provider="kimi")

    def analyze_commentary(self, symbol: str, signal_data: dict) -> str:
        """
        Sinyal verilerini Kimi'ye sorarak yorumlat.
        Returns: AI yorum metni veya fallback mesaj
        """
        if not self.client.is_configured() and not self.client._ollama_fallback.is_available():
            return f"{symbol}: Bulut token yok ve Ollama offline — teknik skor {signal_data.get('score', 'N/A')}"

        prompt = f"""Sen bir Borsa İstanbul teknik analistisisin. Aşağıdaki hisse verisini Türkçe, profesyonel ama anlaşılır şekilde yorumla.

Hisse: {symbol}
Sinyal Skoru: {signal_data.get('score', 'N/A')}
Giriş Fiyatı: {signal_data.get('entry', 'N/A')}
Stop Loss: {signal_data.get('sl', 'N/A')}
Take Profit 1: {signal_data.get('tp1', 'N/A')}
R:R Oranı: {signal_data.get('r_r', 'N/A')}
Kelly Katsayısı: {signal_data.get('kelly', 'N/A')}
Piyasa Rejimi: {signal_data.get('regime', 'N/A')}

Kısa yorum (2-3 cümle):"""

        result = self.client.generate(prompt)
        if result.get("error"):
            return f"{symbol}: AI yorum alınamadi — {result['error']}"
        return result.get("response", "")


class RiskAgentAI:
    """
    Risk Ajanı için Kimi/Bulut entegrasyonu.
    Risk metriklerini doğal dil özetine çevirir.
    """

    def __init__(self, client: Optional[CloudClient] = None):
        self.client = client or CloudClient(provider="kimi")

    def risk_summary(self, metrics: dict) -> str:
        """Risk metriklerini AI ile özetle."""
        if not self.client.is_configured() and not self.client._ollama_fallback.is_available():
            return "Risk AI: Bulut token yok ve Ollama offline."

        prompt = f"""Sen bir risk yöneticisisin. Aşağıdaki risk metriklerini Türkçe, kısa ve öz şekilde yorumla.

Max Drawdown: {metrics.get('max_drawdown', 'N/A')}%
Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}
Win Rate: {metrics.get('win_rate', 'N/A')}%
Daily PnL: {metrics.get('daily_pnl', 'N/A')}

Kısa risk yorumu (1-2 cümle):"""

        result = self.client.generate(prompt)
        if result.get("error"):
            return f"Risk AI: {result['error']}"
        return result.get("response", "")


class StrategyAgentAI:
    """
    Strateji Ajanı için Kimi/Bulut entegrasyonu.
    Nihai karar gerekcelerini doğal dil açıklamasına çevirir.
    """

    def __init__(self, client: Optional[CloudClient] = None):
        self.client = client or CloudClient(provider="kimi")

    def decision_rationale(self, symbol: str, context: dict) -> str:
        """
        Sinyal ve Risk çıktılarını Kimi'ye sorarak nihai karar gerekçesi üret.
        Returns: AI gerekce metni veya fallback mesaj
        """
        if not self.client.is_configured() and not self.client._ollama_fallback.is_available():
            return f"{symbol}: Bulut token yok ve Ollama offline — Strateji Ajanı manuel karar."

        prompt = f"""Sen bir portföy yöneticisisin. Aşağıdaki hisse verisini değerlendir ve
Türkçe, kısa ve öz bir nihai karar gerekçesi yaz.

Hisse: {symbol}
Sinyal Skoru: {context.get('signal_score', 'N/A')}
Risk Etiketi: {context.get('risk_label', 'N/A')}
Piyasa Rejimi: {context.get('regime', 'N/A')}
Kelly Katsayısı: {context.get('kelly', 'N/A')}
R:R Oranı: {context.get('r_r', 'N/A')}

Nihai karar gerekçesi (1-2 cümle):"""

        result = self.client.generate(prompt)
        if result.get("error"):
            return f"{symbol}: AI gerekce alınamadı — {result['error']}"
        return result.get("response", "")


if __name__ == "__main__":
    client = CloudClient()
    print("Kimi token var mi:", client.is_configured())
    r = client.generate("Merhaba, bugun BIST100 nasil?")
    print("Yanut:", r.get("response"), "| Provider:", r.get("provider"), "| Hata:", r.get("error"))

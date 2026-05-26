"""
ollama_client.py — Ollama API Client (Local, Token Yok)
localhost:11434 uzerinden Gemma/Llama/Mistral calistirir.

Kullanim:
    from ai.ollama_client import OllamaClient
    client = OllamaClient()
    response = client.generate("THYAO teknik analizi yap", model="gemma")
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import json
import requests
from typing import Optional


DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaClient:
    """
    Ollama API istemcisi. Localhost uzerinden calisir, token gerektirmez.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def is_available(self) -> bool:
        """Ollama servisi calisiyor mu?"""
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, model: str = "gemma", stream: bool = False) -> dict:
        """
        Ollama'dan text uret.
        Returns: {"response": str, "done": bool, "error": str|None}
        """
        if not self.is_available():
            return {"response": "", "done": False, "error": "Ollama servisi bulunamadi (localhost:11434)"}

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {"temperature": 0.7, "num_predict": 512},
            }
            resp = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "response": data.get("response", "").strip(),
                "done": data.get("done", True),
                "error": None,
            }
        except requests.exceptions.ConnectionError:
            return {"response": "", "done": False, "error": "Ollama baglantisi reddedildi. Servis calisiyor mu?"}
        except Exception as e:
            return {"response": "", "done": False, "error": str(e)}

    def list_models(self) -> list[str]:
        """Yuklu modelleri listele."""
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []


if __name__ == "__main__":
    client = OllamaClient()
    print("Ollama calisiyor mu:", client.is_available())
    print("Modeller:", client.list_models())
    if client.is_available():
        r = client.generate("BIST100 bugun nasil?", model="gemma")
        print("Yanut:", r.get("response"))

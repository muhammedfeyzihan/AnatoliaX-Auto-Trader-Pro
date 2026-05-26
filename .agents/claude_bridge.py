"""
claude_bridge.py — Claude Code CLI sarmalayıcı ve orkestrasyon
"""
import subprocess
from typing import List, Optional


class ClaudeCodeCLI:
    """
    Claude Code CLI (`claude dev`) sarmalayıcı.

    Ozellikler:
    - `claude dev --prompt "..."` ile calistirma
    - Cikti yakalama ve ayrıstırma
    - Calisma dizini belirleme
    """

    def __init__(self, cwd: str = "."):
        self.cwd = cwd

    def run(self, prompt: str, timeout_sec: int = 300) -> str:
        """Claude Code CLI'yi calistir ve ciktiyi dondur."""
        try:
            result = subprocess.run(
                ["claude", "dev", "--prompt", prompt],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=self.cwd,
            )
            return result.stdout + result.stderr
        except FileNotFoundError:
            return "HATA: claude komutu bulunamadi."
        except subprocess.TimeoutExpired:
            return "HATA: Zaman asimi."


class ClaudeBridge:
    """
    Claude icin paylasimli bellek entegrasyonu.

    Kullanim:
        bridge = ClaudeBridge(shared_memory)
        bridge.submit_task("Implement GPU scheduler")
        status = bridge.get_status()
    """

    def __init__(self, shared_memory=None):
        self._sm = shared_memory
        self._cli = ClaudeCodeCLI()

    def submit_task(self, description: str) -> str:
        """Gorevi paylasimli bellege yaz ve Claude CLI'yi calistir."""
        if self._sm:
            self._sm.append_task(agent="Claude", description=description)
        return self._cli.run(description)

    def get_status(self) -> dict:
        """Son calisma durumunu dondur."""
        return {"agent": "Claude", "status": "idle"}

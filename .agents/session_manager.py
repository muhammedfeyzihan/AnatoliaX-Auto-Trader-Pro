"""
.agents/session_manager.py — Claude Code oturum yonetimi
"""
from datetime import datetime
from typing import Dict, Optional


class SessionManager:
    """
    Claude Code oturumlarini izler: baslangic, bitis, context boyutu, maliyet.

    K190: Oturum basina maliyet takibi yapilir; limit asiminda uyarilir.
    """

    def __init__(self):
        self.sessions: Dict[str, dict] = {}

    def start(self, session_id: str) -> None:
        self.sessions[session_id] = {
            "start": datetime.utcnow().isoformat(),
            "end": None,
            "commands": 0,
        }

    def end(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["end"] = datetime.utcnow().isoformat()

    def log_command(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["commands"] += 1

    def get_summary(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

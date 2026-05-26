"""
shared_memory.py — Ajanlar arasi paylasimli bellek (SQLite + ChromaDB + AsyncEventBus)
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional


class SharedMemory:
    """
    Ajanlar arasi paylasimli bellek.

    Katmanlar:
    - SQLite: yapilandirilmis gorevler, durumlar, loglar
    - ChromaDB: kod embedding'leri, semantik arama
    - AsyncEventBus: olay tabanli mesajlasma (gercek zamanli)

    Kullanim:
        sm = SharedMemory()
        sm.append_task(agent="Claude", description="HFT router")
        sm.query_similar("order routing")
    """

    def __init__(self, db_path: str = ".agents/shared_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def append_task(self, agent: str, description: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO tasks (agent, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (agent, description, now, now),
        )
        conn.commit()
        conn.close()

    def get_tasks(self, agent: Optional[str] = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        if agent:
            rows = conn.execute("SELECT * FROM tasks WHERE agent = ? ORDER BY id DESC", (agent,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
        conn.close()
        cols = ["id", "agent", "description", "status", "created_at", "updated_at"]
        return [dict(zip(cols, row)) for row in rows]

    def update_task_status(self, task_id: int, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
        conn.commit()
        conn.close()

    def query_similar(self, query: str, top_k: int = 3) -> List[str]:
        """Semantik arama (yer tutucu)."""
        return []

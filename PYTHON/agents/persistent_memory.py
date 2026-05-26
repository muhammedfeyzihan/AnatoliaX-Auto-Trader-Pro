"""
persistent_memory.py — Unified agent memory (SQLite + ChromaDB fallback).
K226: PersistentAgentMemory.
"""
import sqlite3
import json
import os
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


@dataclass
class MemoryEntry:
    agent: str = ""
    category: str = "decision"
    content: str = ""
    embedding_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PersistentAgentMemory:
    """
    Ajan hafizasi: SQLite tabanli ana kayit + ChromaDB embedding (opsiyonel).
    """

    def __init__(self, db_path: str = "agent_memory.db", chroma_path: Optional[str] = None):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self._chroma = None
        self._collection = None
        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT,
                category TEXT,
                content TEXT,
                embedding_id TEXT,
                metadata TEXT,
                created_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON memory(agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memory(category)")
        conn.commit()
        conn.close()

    def _init_chroma(self):
        if self.chroma_path:
            try:
                import chromadb
                self._chroma = chromadb.PersistentClient(path=self.chroma_path)
                self._collection = self._chroma.get_or_create_collection("agent_memory")
            except Exception:
                pass

    def store(self, entry: MemoryEntry) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "INSERT INTO memory (agent, category, content, embedding_id, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entry.agent, entry.category, entry.content, entry.embedding_id, json.dumps(entry.metadata), entry.created_at),
        )
        mem_id = str(cursor.lastrowid)
        conn.commit()
        conn.close()

        if self._collection:
            try:
                self._collection.add(
                    ids=[mem_id],
                    documents=[entry.content],
                    metadatas=[{"agent": entry.agent, "category": entry.category}],
                )
            except Exception:
                pass
        return mem_id

    def recall(self, agent: str, category: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        conn = sqlite3.connect(self.db_path)
        if category:
            rows = conn.execute(
                "SELECT agent, category, content, embedding_id, metadata, created_at FROM memory WHERE agent = ? AND category = ? ORDER BY created_at DESC LIMIT ?",
                (agent, category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent, category, content, embedding_id, metadata, created_at FROM memory WHERE agent = ? ORDER BY created_at DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
        conn.close()
        return [
            MemoryEntry(
                agent=r[0], category=r[1], content=r[2], embedding_id=r[3],
                metadata=json.loads(r[4]), created_at=r[5],
            )
            for r in rows
        ]

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        if not self._collection:
            return []
        try:
            results = self._collection.query(query_texts=[query], n_results=limit)
            out = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                out.append({
                    "content": doc,
                    "metadata": results.get("metadatas", [[]])[0][i],
                    "distance": results.get("distances", [[]])[0][i],
                })
            return out
        except Exception:
            return []

    def forget_old(self, agent: str, days: int = 30):
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM memory WHERE agent = ? AND created_at < ?",
            (agent, cutoff),
        )
        conn.commit()
        conn.close()

    def get_stats(self, agent: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM memory WHERE agent = ?", (agent,)).fetchone()[0]
        categories = conn.execute(
            "SELECT category, COUNT(*) FROM memory WHERE agent = ? GROUP BY category",
            (agent,),
        ).fetchall()
        conn.close()
        return {"total_entries": total, "categories": {c: n for c, n in categories}}

    def reset(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM memory")
        conn.commit()
        conn.close()
        if self._collection:
            try:
                self._chroma.delete_collection("agent_memory")
                self._collection = self._chroma.get_or_create_collection("agent_memory")
            except Exception:
                pass

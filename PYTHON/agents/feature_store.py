"""
feature_store.py — Shared engineered features storage.
K235: FeatureStore.
"""
import sqlite3
import json
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class FeatureStore:
    """
    Ortak feature store: stratejiler arasi feature paylasimi.
    SQLite tabanli, key-value + time-series.
    """

    def __init__(self, db_path: str = "feature_store.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                feature_name TEXT,
                value REAL,
                timestamp TEXT,
                metadata TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sym_feat ON features(symbol, feature_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON features(timestamp)")
        conn.commit()
        conn.close()

    def store(self, symbol: str, feature_name: str, value: float, timestamp: Optional[str] = None, metadata: Optional[Dict] = None):
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO features (symbol, feature_name, value, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (symbol, feature_name, value, ts, json.dumps(metadata or {})),
            )
            conn.commit()
        finally:
            conn.close()

    def get_latest(self, symbol: str, feature_name: str) -> Optional[float]:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT value FROM features WHERE symbol = ? AND feature_name = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol, feature_name),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_history(self, symbol: str, feature_name: str, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT value, timestamp, metadata FROM features WHERE symbol = ? AND feature_name = ? ORDER BY timestamp DESC LIMIT ?",
                (symbol, feature_name, limit),
            ).fetchall()
            return [{"value": r[0], "timestamp": r[1], "metadata": json.loads(r[2])} for r in rows]
        finally:
            conn.close()

    def get_features_for_symbol(self, symbol: str, timestamp: Optional[str] = None) -> Dict[str, float]:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT feature_name, value FROM features
                WHERE symbol = ? AND timestamp <= ?
                AND id IN (
                    SELECT MAX(id) FROM features WHERE symbol = ? AND timestamp <= ? GROUP BY feature_name
                )
                """,
                (symbol, ts, symbol, ts),
            ).fetchall()
            return {r[0]: r[1] for r in rows}
        finally:
            conn.close()

    def get_all_symbols(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute("SELECT DISTINCT symbol FROM features").fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def reset(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM features")
            conn.commit()
        finally:
            conn.close()

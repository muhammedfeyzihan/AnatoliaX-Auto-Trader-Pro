"""
adapters/questdb_adapter.py — QuestDB Time-Series Adapter

Provides SQL interface to QuestDB for fast time-series queries.
Falls back to SQLite if QuestDB (psycopg2/questdb) unavailable.

Reference: https://questdb.io/
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


class QuestDBAdapter:
    """
    QuestDB SQL interface for tick/bar time-series storage.
    Uses PostgreSQL wire protocol. Falls back to SQLite.
    """

    def __init__(self, host: str = "localhost", port: int = 8812,
                 db: str = "qdb", user: str = "admin", password: str = "quest"):
        self.dsn = f"host={host} port={port} dbname={db} user={user} password={password}"
        self._conn = None
        try:
            import psycopg2
            self._conn = psycopg2.connect(self.dsn)
        except Exception:
            pass
        self._sqlite_fallback = sqlite3.connect("questdb_fallback.db")
        self._sqlite_fallback.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                symbol TEXT, timestamp TEXT, price REAL, size REAL
            )
        """)
        self._sqlite_fallback.commit()

    def insert_ticks(self, symbol: str, df: pd.DataFrame) -> bool:
        if self._conn is not None:
            try:
                from io import StringIO
                buffer = StringIO()
                df.to_csv(buffer, index=False, header=False)
                buffer.seek(0)
                cursor = self._conn.cursor()
                cursor.copy_from(buffer, "ticks", sep=",", columns=("symbol", "timestamp", "price", "size"))
                self._conn.commit()
                return True
            except Exception:
                pass
        # SQLite fallback
        for _, row in df.iterrows():
            self._sqlite_fallback.execute(
                "INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)",
                (symbol, str(row.get("timestamp", "")), float(row.get("price", 0)), float(row.get("size", 0)))
            )
        self._sqlite_fallback.commit()
        return True

    def query(self, sql: str) -> pd.DataFrame:
        if self._conn is not None:
            try:
                return pd.read_sql(sql, self._conn)
            except Exception:
                pass
        return pd.read_sql(sql.replace("SAMPLE BY", "GROUP BY").replace("LATEST ON", "ORDER BY"), self._sqlite_fallback)

    def get_info(self) -> Dict:
        return {
            "adapter": "QuestDBAdapter",
            "dsn": self.dsn,
            "connected": self._conn is not None,
        }

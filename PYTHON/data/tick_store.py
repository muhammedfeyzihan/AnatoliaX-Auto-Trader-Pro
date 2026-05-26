"""
tick_store.py — Tick database, parquet pipeline, historical replay engine
"""
import os
import sqlite3
import pandas as pd
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from pathlib import Path


class TickStore:
    """
    SQLite tick DB + Parquet archive.
    Canli tick'leri SQLite'e yazar, gun sonu Parquet'e arsivler.
    Historical replay: Parquet'tan okuyarak eski piyasayi simule eder.
    """

    def __init__(self, db_path: str = "data/ticks.db", parquet_dir: str = "data/parquet"):
        self.db_path = db_path
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL,
                bid REAL,
                ask REAL,
                source TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks(symbol, timestamp)")
        conn.commit()
        conn.close()

    def insert(self, symbol: str, timestamp: datetime, price: float, size: float = 0.0,
               bid: float = None, ask: float = None, source: str = "live"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO ticks (symbol, timestamp, price, size, bid, ask, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol.upper(), timestamp.isoformat(), price, size, bid, ask, source),
        )
        conn.commit()
        conn.close()

    def get_range(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM ticks WHERE symbol = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            conn,
            params=(symbol.upper(), start.isoformat(), end.isoformat()),
        )
        conn.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def archive_to_parquet(self, date: datetime = None):
        """Gun sonu SQLite tick'lerini Parquet'e yaz."""
        date = date or datetime.now(timezone.utc)
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM ticks WHERE timestamp >= ? AND timestamp < ?",
            conn,
            params=(start.isoformat(), end.isoformat()),
        )
        conn.close()

        if df.empty:
            return None

        path = self.parquet_dir / f"ticks_{date.strftime('%Y%m%d')}.parquet"
        if _HAS_PYARROW:
            table = pa.Table.from_pandas(df)
            pq.write_table(table, path)
        else:
            df.to_parquet(path)
        return path

    def load_parquet(self, date: datetime) -> pd.DataFrame:
        path = self.parquet_dir / f"ticks_{date.strftime('%Y%m%d')}.parquet"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)

    def replay(self, symbol: str, date: datetime, speed: float = 1.0):
        """Historical replay generator: gercek tick'leri hizli/ yavas oynatir."""
        import time
        df = self.load_parquet(date)
        df = df[df["symbol"] == symbol.upper()].sort_values("timestamp")
        if df.empty:
            return

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        for i, row in df.iterrows():
            yield row.to_dict()
            if i + 1 < len(df):
                next_ts = df.iloc[i + 1]["timestamp"]
                delta = (next_ts - row["timestamp"]).total_seconds()
                if delta > 0:
                    time.sleep(delta / speed)

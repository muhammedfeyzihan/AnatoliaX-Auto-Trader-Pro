"""
catalog.py — Unified Data Catalog (Parquet + PyArrow Dataset).
Inspired by Nautilus Trader's DataCatalog.

Provides a single source of truth for historical market data:
- Bar (OHLCV) and tick data stored as Parquet
- Metadata schema tracking (symbol, interval, date range, source)
- Fast querying via PyArrow Dataset (if available) or pandas
- Integration with existing TickStore for tick replay
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyarrow.dataset as ds
    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False


class DataCatalog:
    """
    Unified Parquet-based data catalog.

    Directory layout:
        catalog/
        ├── bars/
        │   ├── THYAO/
        │   │   ├── 1d/
        │   │   │   ├── 2026-01-01.parquet
        │   │   │   └── 2026-01-02.parquet
        │   │   └── 15m/
        │   └── GARAN/
        ├── ticks/
        │   ├── THYAO/
        │   │   └── 2026-01.parquet
        │   └── GARAN/
        └── catalog.db   (metadata index)
    """

    def __init__(self, base_dir: str = "data/catalog"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "bars").mkdir(exist_ok=True)
        (self.base_dir / "ticks").mkdir(exist_ok=True)

        self.db_path = self.base_dir / "catalog.db"
        self._init_db()

    # ------------------------------------------------------------------
    # Internal — SQLite metadata index
    # ------------------------------------------------------------------
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS catalog_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                data_type TEXT NOT NULL,   -- 'bar' | 'tick'
                interval TEXT,             -- '1d', '15m', etc. (NULL for ticks)
                file_path TEXT NOT NULL,
                date_from TEXT,
                date_to TEXT,
                rows INTEGER,
                created_at TEXT,
                source TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cat_symbol_type
            ON catalog_meta(symbol, data_type, interval)
        """)
        conn.commit()
        conn.close()

    def _meta_insert(self, meta: dict):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO catalog_meta
               (symbol, data_type, interval, file_path, date_from, date_to, rows, created_at, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meta["symbol"].upper(),
                meta["data_type"],
                meta.get("interval"),
                meta["file_path"],
                meta.get("date_from"),
                meta.get("date_to"),
                meta.get("rows"),
                meta.get("created_at", datetime.now(timezone.utc).isoformat()),
                meta.get("source", "unknown"),
            ),
        )
        conn.commit()
        conn.close()

    def _meta_query(self, symbol: str, data_type: str, interval: Optional[str] = None) -> List[dict]:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        if interval:
            c.execute(
                "SELECT file_path, date_from, date_to, rows, source FROM catalog_meta "
                "WHERE symbol = ? AND data_type = ? AND interval = ? ORDER BY date_from",
                (symbol.upper(), data_type, interval),
            )
        else:
            c.execute(
                "SELECT file_path, date_from, date_to, rows, source FROM catalog_meta "
                "WHERE symbol = ? AND data_type = ? ORDER BY date_from",
                (symbol.upper(), data_type),
            )
        rows = c.fetchall()
        conn.close()
        return [
            {
                "file_path": r[0],
                "date_from": r[1],
                "date_to": r[2],
                "rows": r[3],
                "source": r[4],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Public — Write
    # ------------------------------------------------------------------
    def write_bars(
        self,
        symbol: str,
        df: pd.DataFrame,
        interval: str = "1d",
        source: str = "unknown",
        overwrite: bool = False,
    ) -> Path:
        """
        Write an OHLCV DataFrame to Parquet, partitioned by symbol/interval/date.
        Expects df columns: timestamp, open, high, low, close, volume
        """
        if df.empty:
            raise ValueError("Cannot write empty DataFrame to catalog")

        df = df.copy()
        if "timestamp" not in df.columns:
            raise ValueError("DataFrame must contain a 'timestamp' column")

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date.astype(str)

        sym_dir = self.base_dir / "bars" / symbol.upper() / interval
        sym_dir.mkdir(parents=True, exist_ok=True)

        # Write one file per calendar date
        written_paths = []
        for date_str, group in df.groupby("date"):
            path = sym_dir / f"{date_str}.parquet"
            if path.exists() and not overwrite:
                # Append by reading existing, concatenating, deduping
                existing = pd.read_parquet(path)
                combined = pd.concat([existing, group.drop(columns=["date"])], ignore_index=True)
                combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
            else:
                combined = group.drop(columns=["date"]).sort_values("timestamp")

            if _HAS_PYARROW:
                table = pa.Table.from_pandas(combined)
                pq.write_table(table, path)
            else:
                combined.to_parquet(path, index=False)

            written_paths.append(path)

            self._meta_insert({
                "symbol": symbol,
                "data_type": "bar",
                "interval": interval,
                "file_path": str(path),
                "date_from": date_str,
                "date_to": date_str,
                "rows": len(combined),
                "source": source,
            })

        return sym_dir

    def write_ticks(
        self,
        symbol: str,
        df: pd.DataFrame,
        month: str,  # "YYYY-MM"
        source: str = "unknown",
        overwrite: bool = False,
    ) -> Path:
        """Write tick DataFrame to Parquet, partitioned by symbol/month."""
        if df.empty:
            raise ValueError("Cannot write empty tick DataFrame to catalog")

        sym_dir = self.base_dir / "ticks" / symbol.upper()
        sym_dir.mkdir(parents=True, exist_ok=True)
        path = sym_dir / f"{month}.parquet"

        if path.exists() and not overwrite:
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
            if "timestamp" in combined.columns:
                combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        else:
            combined = df

        if _HAS_PYARROW:
            table = pa.Table.from_pandas(combined)
            pq.write_table(table, path)
        else:
            combined.to_parquet(path, index=False)

        date_from = str(combined["timestamp"].min()) if "timestamp" in combined.columns else None
        date_to = str(combined["timestamp"].max()) if "timestamp" in combined.columns else None

        self._meta_insert({
            "symbol": symbol,
            "data_type": "tick",
            "interval": None,
            "file_path": str(path),
            "date_from": date_from,
            "date_to": date_to,
            "rows": len(combined),
            "source": source,
        })

        return path

    # ------------------------------------------------------------------
    # Public — Read
    # ------------------------------------------------------------------
    def read_bars(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Read OHLCV bars from catalog for a symbol + interval + optional date range.
        Uses PyArrow Dataset (fast) if available, else pandas concatenation.
        """
        sym_dir = self.base_dir / "bars" / symbol.upper() / interval
        if not sym_dir.exists():
            return pd.DataFrame()

        files = sorted(sym_dir.glob("*.parquet"))
        if not files:
            return pd.DataFrame()

        # Filter by date range from filename
        if start:
            start_str = start.date().isoformat()
            files = [f for f in files if f.stem >= start_str]
        if end:
            end_str = end.date().isoformat()
            files = [f for f in files if f.stem <= end_str]

        if not files:
            return pd.DataFrame()

        if _HAS_PYARROW:
            dataset = ds.dataset([str(f) for f in files], format="parquet")
            table = dataset.to_table()
            df = table.to_pandas()
        else:
            dfs = [pd.read_parquet(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])

        if start:
            start_cmp = start.replace(tzinfo=None) if df["timestamp"].dt.tz is None and start.tzinfo else start
            df = df[df["timestamp"] >= start_cmp]
        if end:
            end_cmp = end.replace(tzinfo=None) if df["timestamp"].dt.tz is None and end.tzinfo else end
            df = df[df["timestamp"] <= end_cmp]

        return df.reset_index(drop=True)

    def read_ticks(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Read tick data from catalog for a symbol + optional date range."""
        sym_dir = self.base_dir / "ticks" / symbol.upper()
        if not sym_dir.exists():
            return pd.DataFrame()

        files = sorted(sym_dir.glob("*.parquet"))
        if not files:
            return pd.DataFrame()

        if _HAS_PYARROW:
            dataset = ds.dataset([str(f) for f in files], format="parquet")
            table = dataset.to_table()
            df = table.to_pandas()
        else:
            dfs = [pd.read_parquet(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            if start:
                start_cmp = start.replace(tzinfo=None) if df["timestamp"].dt.tz is None and start.tzinfo else start
                df = df[df["timestamp"] >= start_cmp]
            if end:
                end_cmp = end.replace(tzinfo=None) if df["timestamp"].dt.tz is None and end.tzinfo else end
                df = df[df["timestamp"] <= end_cmp]

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Public — Catalog introspection
    # ------------------------------------------------------------------
    def list_symbols(self, data_type: Optional[str] = None) -> List[str]:
        """Return all symbols present in the catalog."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        if data_type:
            c.execute(
                "SELECT DISTINCT symbol FROM catalog_meta WHERE data_type = ? ORDER BY symbol",
                (data_type,),
            )
        else:
            c.execute("SELECT DISTINCT symbol FROM catalog_meta ORDER BY symbol")
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        return rows

    def list_intervals(self, symbol: str) -> List[str]:
        """Return all bar intervals available for a symbol."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            "SELECT DISTINCT interval FROM catalog_meta WHERE symbol = ? AND data_type = 'bar' ORDER BY interval",
            (symbol.upper(),),
        )
        rows = [r[0] for r in c.fetchall() if r[0]]
        conn.close()
        return rows

    def get_coverage(self, symbol: str, interval: str = "1d") -> Dict[str, Any]:
        """Return date coverage and row count for a symbol/interval."""
        meta = self._meta_query(symbol, "bar", interval)
        if not meta:
            return {"symbol": symbol, "interval": interval, "files": 0, "rows": 0, "date_from": None, "date_to": None}

        total_rows = sum(m["rows"] or 0 for m in meta)
        dates = [m["date_from"] for m in meta if m["date_from"]]
        return {
            "symbol": symbol,
            "interval": interval,
            "files": len(meta),
            "rows": total_rows,
            "date_from": min(dates) if dates else None,
            "date_to": max(dates) if dates else None,
        }

    def stats(self) -> dict:
        """Overall catalog statistics."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*), COUNT(DISTINCT symbol), COUNT(DISTINCT data_type) FROM catalog_meta")
        total, unique_symbols, unique_types = c.fetchone()
        conn.close()
        return {
            "total_files": total,
            "unique_symbols": unique_symbols,
            "unique_data_types": unique_types,
            "base_dir": str(self.base_dir),
        }

    def delete_symbol(self, symbol: str, data_type: Optional[str] = None):
        """Remove all catalog entries (and files) for a symbol."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        if data_type:
            c.execute("SELECT file_path FROM catalog_meta WHERE symbol = ? AND data_type = ?", (symbol.upper(), data_type))
        else:
            c.execute("SELECT file_path FROM catalog_meta WHERE symbol = ?", (symbol.upper(),))
        files = [r[0] for r in c.fetchall()]

        for f in files:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass

        if data_type:
            c.execute("DELETE FROM catalog_meta WHERE symbol = ? AND data_type = ?", (symbol.upper(), data_type))
        else:
            c.execute("DELETE FROM catalog_meta WHERE symbol = ?", (symbol.upper(),))
        conn.commit()
        conn.close()

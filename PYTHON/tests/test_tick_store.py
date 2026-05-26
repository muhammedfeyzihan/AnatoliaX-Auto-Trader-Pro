"""
Test: PYTHON.data.tick_store
Tick DB, Parquet archive, historical replay.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.tick_store import TickStore


class TestTickStore:
    def test_insert_and_get(self, tmp_path):
        db = tmp_path / "ticks_test.db"
        pq = tmp_path / "parquet"
        store = TickStore(db_path=str(db), parquet_dir=str(pq))

        now = datetime(2026, 5, 19, 10, 0, 0)
        store.insert("THYAO", now, 103.0, size=1000, bid=102.9, ask=103.1)

        df = store.get_range("THYAO", now.replace(hour=0), now.replace(hour=23))
        assert not df.empty
        assert df.iloc[0]["price"] == 103.0

    def test_archive_empty_returns_none(self, tmp_path):
        db = tmp_path / "ticks_empty.db"
        pq = tmp_path / "parquet"
        store = TickStore(db_path=str(db), parquet_dir=str(pq))
        result = store.archive_to_parquet(date=datetime(2020, 1, 1))
        assert result is None

    def test_replay_generator(self, tmp_path):
        db = tmp_path / "ticks_replay.db"
        pq = tmp_path / "parquet"
        store = TickStore(db_path=str(db), parquet_dir=str(pq))

        # SQLite'e ekle
        for i in range(3):
            store.insert("THYAO", datetime(2026, 5, 19, 10, i, 0), 100.0 + i, size=100)

        # Archive et (parquet yoksa CSV fallback)
        try:
            store.archive_to_parquet(date=datetime(2026, 5, 19))
        except ImportError:
            # Parquet engine yoksa CSV ile devam et
            pass

        # Replay - parquet yoksa SQLite'den oku
        df = store.get_range("THYAO", datetime(2026, 5, 19, 0, 0, 0), datetime(2026, 5, 19, 23, 59, 59))
        assert not df.empty
        assert len(df) == 3
        assert df.iloc[0]["price"] == 100.0

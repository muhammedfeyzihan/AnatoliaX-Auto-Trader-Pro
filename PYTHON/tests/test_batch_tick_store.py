"""
test_batch_tick_store.py — Tests for BatchTickStore (K240)
"""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimization.batch_tick_store import BatchTickStore


class TestBatchTickStore:
    def setup_method(self):
        import uuid
        self.db = f"batch_ticks_test_{uuid.uuid4().hex[:8]}.db"
        self.store = BatchTickStore(db_path=self.db, batch_size=5, flush_interval_sec=60)
        self.store.start()

    def teardown_method(self):
        self.store.stop()
        if Path(self.db).exists():
            os.remove(self.db)

    def test_insert_and_get_range(self):
        now = datetime.now(timezone.utc)
        for i in range(10):
            self.store.insert_tick("THYAO", now, 100.0 + i, 1000)
        self.store.flush()
        df = self.store.get_range("THYAO", now, now)
        assert len(df) >= 10

    def test_batch_insert(self):
        ticks = [
            {"symbol": "THYAO", "timestamp": datetime.now(timezone.utc), "price": 100.0 + i, "size": 100}
            for i in range(20)
        ]
        self.store.insert_ticks(ticks)
        self.store.flush()
        df = self.store.get_range("THYAO", datetime(2000, 1, 1, tzinfo=timezone.utc), datetime(2099, 1, 1, tzinfo=timezone.utc))
        assert len(df) == 20

    def test_replay_numpy(self):
        now = datetime.now(timezone.utc)
        for i in range(10):
            self.store.insert_tick("THYAO", now, 100.0 + i, 1000)
        self.store.flush()
        self.store.archive_to_parquet(now)
        items = list(self.store.replay_numpy("THYAO", now))
        assert len(items) >= 10
        assert "price" in items[0]

    def test_stats(self):
        stats = self.store.stats()
        assert "buffered_ticks" in stats
        assert "db_total_ticks" in stats

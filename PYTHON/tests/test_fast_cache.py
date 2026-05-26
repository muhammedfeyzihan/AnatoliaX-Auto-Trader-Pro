"""
test_fast_cache.py — Tests for FastCacheManager (K238)
"""
import pytest
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimization.fast_cache import FastCacheManager


class TestFastCacheManager:
    def setup_method(self):
        import uuid
        self.db = f"fast_cache_test_{uuid.uuid4().hex[:8]}.db"
        # Monkey-patch CACHE_DB for test isolation
        import optimization.fast_cache as fc
        self._orig_db = fc.CACHE_DB
        fc.CACHE_DB = Path(self.db)
        self.cache = FastCacheManager(ttl_seconds=3600, memory_size=10)

    def teardown_method(self):
        import optimization.fast_cache as fc
        fc.CACHE_DB = self._orig_db
        self.cache.close()
        if Path(self.db).exists():
            os.remove(self.db)

    def test_memory_get_set(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        self.cache.set("THYAO", "1d", df, "yahoo")
        retrieved = self.cache.get("THYAO", "1d", "yahoo")
        assert retrieved is not None
        assert retrieved.equals(df)

    def test_memory_lru_eviction(self):
        cache = FastCacheManager(ttl_seconds=3600, memory_size=2)
        cache.set("A", "1d", pd.DataFrame({"x": [1]}))
        cache.set("B", "1d", pd.DataFrame({"x": [2]}))
        cache.set("C", "1d", pd.DataFrame({"x": [3]}))
        # A should be evicted from memory
        assert cache._mem_get("A::1d::DEFAULT") is None
        assert cache._mem_get("B::1d::DEFAULT") is not None
        assert cache._mem_get("C::1d::DEFAULT") is not None
        cache.close()

    def test_db_persistence(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        self.cache.set("GARAN", "1h", df, "tv")
        self.cache.flush()
        # Simulate new instance (memory empty, DB has data)
        self.cache._memory.clear()
        retrieved = self.cache.get("GARAN", "1h", "tv")
        assert retrieved is not None
        assert retrieved.equals(df)

    def test_ttl_expiry(self):
        cache = FastCacheManager(ttl_seconds=-1, memory_size=10)
        df = pd.DataFrame({"x": [1]})
        cache.set("X", "1d", df)
        cache.flush()
        # Clear memory so DB lookup happens (memory doesn't enforce TTL)
        cache._memory.clear()
        # Should be expired immediately due to negative TTL
        retrieved = cache.get("X", "1d")
        assert retrieved is None
        cache.close()

    def test_stats(self):
        self.cache.set("THYAO", "1d", pd.DataFrame({"x": [1]}))
        stats = self.cache.stats()
        assert stats["memory_entries"] >= 1
        assert stats["memory_limit"] == 10

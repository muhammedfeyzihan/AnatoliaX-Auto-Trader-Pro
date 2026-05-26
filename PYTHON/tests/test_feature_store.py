"""
test_feature_store.py — Tests for FeatureStore (K235)
"""
import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.feature_store import FeatureStore


class TestFeatureStore:
    def setup_method(self):
        import uuid
        self.db = f"test_feature_store_{uuid.uuid4().hex[:8]}.db"

    def teardown_method(self):
        if Path(self.db).exists():
            os.remove(self.db)

    def test_store_and_get_latest(self):
        fs = FeatureStore(db_path=self.db)
        fs.store("THYAO", "rsi", 65.5)
        val = fs.get_latest("THYAO", "rsi")
        assert val == pytest.approx(65.5)

    def test_get_history(self):
        fs = FeatureStore(db_path=self.db)
        fs.store("THYAO", "rsi", 60.0, timestamp="2026-05-22T10:00:00")
        fs.store("THYAO", "rsi", 65.0, timestamp="2026-05-22T10:01:00")
        hist = fs.get_history("THYAO", "rsi")
        assert len(hist) == 2
        assert hist[0]["value"] == 65.0

    def test_get_features_for_symbol(self):
        fs = FeatureStore(db_path=self.db)
        fs.store("THYAO", "rsi", 65.0)
        fs.store("THYAO", "ema20", 150.0)
        feats = fs.get_features_for_symbol("THYAO")
        assert "rsi" in feats
        assert "ema20" in feats

    def test_get_all_symbols(self):
        fs = FeatureStore(db_path=self.db)
        fs.store("THYAO", "rsi", 65.0)
        fs.store("GARAN", "rsi", 55.0)
        syms = fs.get_all_symbols()
        assert "THYAO" in syms
        assert "GARAN" in syms

    def test_reset(self):
        fs = FeatureStore(db_path=self.db)
        fs.store("THYAO", "rsi", 65.0)
        fs.reset()
        assert fs.get_latest("THYAO", "rsi") is None

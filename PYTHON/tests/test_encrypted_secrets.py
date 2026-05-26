"""
test_encrypted_secrets.py — Tests for EncryptedSecretManager (K230)
"""
import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.encrypted_secrets import EncryptedSecretManager


class TestEncryptedSecretManager:
    def setup_method(self):
        self.path = "test_secrets.enc"
        if Path(self.path).exists():
            os.remove(self.path)

    def teardown_method(self):
        if Path(self.path).exists():
            os.remove(self.path)

    def test_set_and_get(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        mgr.set("API_KEY", "secret_value")
        assert mgr.get("API_KEY") == "secret_value"

    def test_get_missing(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        assert mgr.get("MISSING") is None

    def test_rotate(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        mgr.set("API_KEY", "old")
        mgr.rotate("API_KEY", "new")
        assert mgr.get("API_KEY") == "new"

    def test_delete(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        mgr.set("API_KEY", "val")
        assert mgr.delete("API_KEY") is True
        assert mgr.get("API_KEY") is None

    def test_list_keys(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        mgr.set("A", "1")
        mgr.set("B", "2")
        keys = mgr.list_keys()
        assert "A" in keys
        assert "B" in keys

    def test_ttl_expiration(self):
        mgr = EncryptedSecretManager(storage_path=self.path, master_key="test123")
        mgr.set("TEMP", "val", ttl_days=0)
        assert mgr.get("TEMP") is None

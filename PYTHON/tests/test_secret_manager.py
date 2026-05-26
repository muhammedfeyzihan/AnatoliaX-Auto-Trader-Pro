"""
Test: PYTHON.risk.secret_manager
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.secret_manager import SecretManager


class TestSecretManager:
    def test_load_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_KEY=test_value\n")
        sm = SecretManager(str(env_file))
        assert sm.get("TEST_KEY") == "test_value"

    def test_get_with_fallback(self):
        sm = SecretManager(env_path="nonexistent.env")
        assert sm.get("MISSING_KEY", "fallback") == "fallback"

    def test_mask(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=abcdef123456\n")
        sm = SecretManager(str(env_file))
        assert sm.mask("API_KEY") == "abc...456"

    def test_validate(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=v1\n")
        sm = SecretManager(str(env_file))
        missing = sm.validate(["KEY1", "KEY2"])
        assert "KEY2" in missing
        assert "KEY1" not in missing

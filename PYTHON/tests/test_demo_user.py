"""
Test: auth/demo_user
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from auth.rbac import RBACManager
from auth.demo_user import ensure_demo_user, add_user_cli


class TestDemoUser:
    def test_ensure_demo_user_creates(self):
        rbac = RBACManager()
        created = ensure_demo_user(rbac)
        assert created is True
        assert "anatoliax_demo" in rbac.list_users()
        assert rbac.authenticate("anatoliax_demo", "demo123_change_me") is True

    def test_ensure_demo_user_idempotent(self):
        rbac = RBACManager()
        ensure_demo_user(rbac)
        created2 = ensure_demo_user(rbac)
        assert created2 is False

    def test_add_user_cli(self):
        rbac = RBACManager()
        ok = add_user_cli(rbac, "test_user", "trader", "password123")
        assert ok is True
        assert rbac.authenticate("test_user", "password123") is True

    def test_add_user_duplicate(self):
        rbac = RBACManager()
        add_user_cli(rbac, "dup", "trader", "pw")
        ok2 = add_user_cli(rbac, "dup", "trader", "pw2")
        assert ok2 is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

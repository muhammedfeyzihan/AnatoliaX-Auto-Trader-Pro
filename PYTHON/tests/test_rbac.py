"""
Test: PYTHON.auth.rbac
Role check, permission, decorator.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from auth.rbac import RBACManager, require_permission


class TestRBACManager:
    def test_add_and_authenticate(self):
        rbac = RBACManager()
        rbac.add_user("ahmet", "trader", "sifre123")
        assert rbac.authenticate("ahmet", "sifre123") is True
        assert rbac.authenticate("ahmet", "yanlis") is False

    def test_unknown_role_raises(self):
        rbac = RBACManager()
        with pytest.raises(ValueError):
            rbac.add_user("x", "unknown", "pass")

    def test_trader_can_trade(self):
        rbac = RBACManager()
        rbac.add_user("trader1", "trader", "pass")
        assert rbac.check("trader1", "trade.execute") is True
        assert rbac.check("trader1", "user.manage") is False

    def test_viewer_cannot_trade(self):
        rbac = RBACManager()
        rbac.add_user("viewer1", "viewer", "pass")
        assert rbac.check("viewer1", "trade.execute") is False
        assert rbac.check("viewer1", "trade.view") is True

    def test_admin_all_permissions(self):
        rbac = RBACManager()
        rbac.add_user("admin1", "admin", "pass")
        assert rbac.check("admin1", "trade.execute") is True
        assert rbac.check("admin1", "config.edit") is True
        assert rbac.check("admin1", "user.manage") is True

    def test_unknown_user(self):
        rbac = RBACManager()
        assert rbac.check("ghost", "trade.execute") is False
        assert rbac.get_role("ghost") is None

    def test_list_users(self):
        rbac = RBACManager()
        rbac.add_user("a", "trader", "p")
        rbac.add_user("b", "viewer", "p")
        assert "a" in rbac.list_users()
        assert "b" in rbac.list_users()

    def test_remove_user(self):
        rbac = RBACManager()
        rbac.add_user("c", "trader", "p")
        assert rbac.remove_user("c") is True
        assert rbac.remove_user("c") is False

    def test_require_permission_decorator(self):
        rbac = RBACManager()
        rbac.add_user("trader1", "trader", "pass")

        @require_permission("trade.execute")
        def place_order(symbol, username):
            return f"{symbol} emri verildi"

        assert place_order("THYAO", username="trader1", rbac=rbac) == "THYAO emri verildi"

    def test_require_permission_denied(self):
        rbac = RBACManager()
        rbac.add_user("viewer1", "viewer", "pass")

        @require_permission("trade.execute")
        def place_order(symbol, username):
            return f"{symbol} emri verildi"

        with pytest.raises(PermissionError):
            place_order("THYAO", username="viewer1", rbac=rbac)

    def test_require_permission_no_username(self):
        @require_permission("trade.execute")
        def place_order(symbol):
            return "ok"

        with pytest.raises(PermissionError):
            place_order("THYAO")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
demo_user.py — Automatic demo user creation for easy onboarding.

Creates a default demo user on first run so humans can log in
without manual RBAC setup. The demo user is clearly marked
and should be replaced in production.

Usage:
    from auth.demo_user import ensure_demo_user
    ensure_demo_user(rbac_manager)

    # CLI: python main.py --add-user <name> <role> <password>
"""

from auth.rbac import RBACManager

DEMO_USERNAME = "anatoliax_demo"
DEMO_PASSWORD = "demo123_change_me"
DEMO_ROLE = "trader"


def ensure_demo_user(rbac: RBACManager) -> bool:
    """Create demo user if it doesn't exist. Returns True if created."""
    if DEMO_USERNAME in rbac.list_users():
        return False
    rbac.add_user(DEMO_USERNAME, DEMO_ROLE, DEMO_PASSWORD)
    return True


def add_user_cli(rbac: RBACManager, username: str, role: str, password: str) -> bool:
    """Add a user via CLI. Returns True if added."""
    if username in rbac.list_users():
        return False
    rbac.add_user(username, role, password)
    return True

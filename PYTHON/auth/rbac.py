"""
rbac.py — Role-Based Access Control (RBAC).
AnatoliaX icin özgün implementasyon.

Kullanim:
    from auth.rbac import RBACManager, require_permission
    rbac = RBACManager()
    rbac.add_user("ahmet", role="trader", password="guclu_sifre")
    if rbac.check("ahmet", "trade.execute"):
        ...
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from typing import Optional, Callable
from functools import wraps


ROLE_PERMISSIONS = {
    "admin": [
        "trade.execute",
        "trade.view",
        "config.edit",
        "report.generate",
        "alert.configure",
        "user.manage",
    ],
    "trader": [
        "trade.execute",
        "trade.view",
        "report.generate",
        "alert.configure",
    ],
    "viewer": [
        "trade.view",
        "report.generate",
    ],
    "system": [
        "trade.execute",
        "trade.view",
        "config.edit",
        "report.generate",
        "alert.configure",
    ],
}


class RBACManager:
    """
    Basit RBAC yonetimi: kullanici, rol, yetki kontrolu.
    Sifreler basit hash ile saklanir (gercek uygulamada bcrypt kullanilir).
    """

    def __init__(self):
        self._users: dict[str, dict] = {}

    def add_user(self, username: str, role: str, password: str):
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"Bilinmeyen rol: {role}. Izin verilenler: {list(ROLE_PERMISSIONS.keys())}")
        self._users[username] = {
            "role": role,
            "password_hash": self._hash(password),
        }

    def authenticate(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        return user["password_hash"] == self._hash(password)

    def check(self, username: str, permission: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        return permission in ROLE_PERMISSIONS.get(user["role"], [])

    def get_role(self, username: str) -> Optional[str]:
        user = self._users.get(username)
        return user["role"] if user else None

    def list_users(self) -> list[str]:
        return list(self._users.keys())

    def remove_user(self, username: str) -> bool:
        if username in self._users:
            del self._users[username]
            return True
        return False

    @staticmethod
    def _hash(password: str) -> str:
        # Basit hash — gercek uygulamada bcrypt/scrypt
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def require_permission(permission: str):
    """
    Decorator: Fonksiyonu cagiran kullanicinin yetkisini kontrol et.
    Kullanim:
        @require_permission("trade.execute")
        def place_order(...):
            ...
    Not: Kullanici adi fonksiyon argumanlarindan 'username' olarak alinir.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = kwargs.get("username")
            if not username:
                # args icinde ara
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if "username" in params:
                    idx = params.index("username")
                    if idx < len(args):
                        username = args[idx]
            if not username:
                raise PermissionError("Kullanici adi bulunamadi (username parametresi gerekli)")

            # Global rbac instance varsayimi (opsiyonel)
            rbac = kwargs.pop("rbac", None)
            if rbac and isinstance(rbac, RBACManager):
                if not rbac.check(username, permission):
                    raise PermissionError(f"'{username}' kullanicisinin '{permission}' yetkisi yok")
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    rbac = RBACManager()
    demo_pw = "demo_sifre_degistir"
    rbac.add_user("ahmet", "trader", demo_pw)
    print(rbac.authenticate("ahmet", demo_pw))
    print(rbac.check("ahmet", "trade.execute"))
    print(rbac.check("ahmet", "user.manage"))

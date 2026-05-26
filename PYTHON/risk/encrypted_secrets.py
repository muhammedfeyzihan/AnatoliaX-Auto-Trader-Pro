"""
encrypted_secrets.py — Encrypted secret storage + rotation.
K230: EncryptedSecretManager.
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone


class EncryptedSecretManager:
    """
    Sifreli secret yonetimi. Fernet sifreleme + rotation.
    Fernet yoksa basit XOR + base64 fallback (dusuk guvenlik).
    """

    def __init__(self, storage_path: str = "secrets.enc", master_key: Optional[str] = None):
        self.storage_path = storage_path
        self._secrets: Dict[str, Dict] = {}
        self._master_key = self._derive_key(master_key or os.getenv("MASTER_KEY", "default"))
        self._cipher = None
        self._load()
        self._init_cipher()

    def _derive_key(self, key: str) -> bytes:
        return hashlib.sha256(key.encode()).digest()

    def _init_cipher(self):
        try:
            from cryptography.fernet import Fernet
            self._cipher = Fernet(base64.urlsafe_b64encode(self._master_key))
        except ImportError:
            self._cipher = None

    def _encrypt(self, plaintext: str) -> str:
        if self._cipher:
            return self._cipher.encrypt(plaintext.encode()).decode()
        # Fallback: XOR + base64 (NOT for production)
        key_bytes = self._master_key
        data = plaintext.encode()
        xor = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
        return base64.b64encode(xor).decode()

    def _decrypt(self, ciphertext: str) -> str:
        if self._cipher:
            return self._cipher.decrypt(ciphertext.encode()).decode()
        key_bytes = self._master_key
        xor = base64.b64decode(ciphertext.encode())
        data = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xor))
        return data.decode()

    def set(self, key: str, value: str, ttl_days: Optional[int] = None):
        self._secrets[key] = {
            "value": self._encrypt(value),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ttl_days": ttl_days,
        }
        self._save()

    def get(self, key: str) -> Optional[str]:
        entry = self._secrets.get(key)
        if not entry:
            return None
        if entry.get("ttl_days") is not None:
            created = datetime.fromisoformat(entry["created_at"])
            if datetime.now(timezone.utc) > created + timedelta(days=entry["ttl_days"]):
                del self._secrets[key]
                self._save()
                return None
        return self._decrypt(entry["value"])

    def rotate(self, key: str, new_value: str):
        """Secret'i yeni deger ile degistir."""
        self.set(key, new_value)

    def delete(self, key: str) -> bool:
        if key in self._secrets:
            del self._secrets[key]
            self._save()
            return True
        return False

    def list_keys(self) -> List[str]:
        return list(self._secrets.keys())

    def _load(self):
        if Path(self.storage_path).exists():
            with open(self.storage_path, "r", encoding="utf-8") as f:
                self._secrets = json.load(f)

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._secrets, f, indent=2)

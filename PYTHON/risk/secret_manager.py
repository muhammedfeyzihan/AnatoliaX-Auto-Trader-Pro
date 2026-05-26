
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
import threading

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

@dataclass
class SecretAuditLog:
    secret_key: str
    action: str
    timestamp: str
    success: bool
    notes: str = ""

class SecretManager:
    SENSITIVE_PATTERNS = ["KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL"]
    
    def __init__(self, env_path=".env", encryption_key=None, enable_audit=True):
        self._secrets = {}
        self._encrypted_secrets = {}
        self._audit_logs = []
        self._lock = threading.RLock()
        self._enable_audit = enable_audit
        self._encryption_key = None
        self._salt = None
        if HAS_CRYPTO and encryption_key:
            self._salt = os.urandom(16)
        self._load_env_file(env_path)
        self._load_os_environ()
    
    def _load_env_file(self, env_path):
        path = Path(env_path)
        if not path.exists(): return
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" not in line: continue
                key, value = line.split("=", 1)
                self._secrets[key.strip()] = value.strip().strip(chr(34)).strip(chr(39))
    
    def _load_os_environ(self):
        for key, value in os.environ.items():
            if key.startswith("ANATOLIAX_") or self._is_sensitive(key):
                self._secrets[key] = value
    
    def _is_sensitive(self, key):
        return any(p in key.upper() for p in self.SENSITIVE_PATTERNS)
    
    def get(self, key, fallback=None):
        with self._lock:
            val = self._secrets.get(key)
            if val is None or val == "": return fallback
            self._audit("get", True, key)
            return val
    
    def get_required(self, key):
        val = self.get(key)
        if val is None: raise KeyError(f"Required secret {key} not found")
        return val
    
    def set(self, key, value, encrypt=False):
        with self._lock:
            self._secrets[key] = value
            os.environ[key] = value
            self._audit("set", True, key)
    
    def has(self, key):
        val = self._secrets.get(key)
        return val is not None and val != ""
    
    def mask(self, key):
        val = self._secrets.get(key)
        if not val or len(val) <= 8: return "***"
        return val[:3] + "..." + val[-3:]
    
    def validate(self, required_keys):
        return [k for k in required_keys if not self.has(k)]
    
    def _audit(self, action, success, key="", notes=""):
        if not self._enable_audit: return
        self._audit_logs.append(SecretAuditLog(secret_key=key, action=action, timestamp=datetime.now(timezone.utc).isoformat(), success=success, notes=notes))
    
    def stats(self):
        return {"total_secrets": len(self._secrets), "encrypted_secrets": len(self._encrypted_secrets), "audit_logs": len(self._audit_logs), "encryption_enabled": HAS_CRYPTO and self._encryption_key is not None}

_secret_manager_instance = None

def get_secret_manager(env_path=".env", encryption_key=None):
    global _secret_manager_instance
    if _secret_manager_instance is None:
        _secret_manager_instance = SecretManager(env_path=env_path, encryption_key=encryption_key)
    return _secret_manager_instance

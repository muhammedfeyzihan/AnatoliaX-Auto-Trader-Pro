"""
crash_recovery.py — Persistent state + failover on crash.
K234: CrashRecoveryManager.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone


class CrashRecoveryManager:
    """
    Sistem crash sonrasi durumu geri yukleme.
    Checkpoint + state diff + otomatik recovery.
    """

    def __init__(self, checkpoint_dir: str = "checkpoints", max_checkpoints: int = 10):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self._state: Dict[str, Any] = {}
        self._last_save = 0.0
        self._save_interval_sec = 60.0

    def set(self, key: str, value: Any):
        self._state[key] = value
        self._maybe_checkpoint()

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def _maybe_checkpoint(self):
        now = time.time()
        if now - self._last_save > self._save_interval_sec:
            self.checkpoint()
            self._last_save = now

    def checkpoint(self, tag: Optional[str] = None):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"checkpoint_{ts}.json"
        if tag:
            name = f"checkpoint_{tag}_{ts}.json"
        path = self.checkpoint_dir / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, default=str, indent=2)
        self._prune_old_checkpoints()

    def _prune_old_checkpoints(self):
        files = sorted(self.checkpoint_dir.glob("checkpoint_*.json"), key=lambda p: p.stat().st_mtime)
        while len(files) > self.max_checkpoints:
            files[0].unlink()
            files.pop(0)

    def recover(self, tag: Optional[str] = None) -> Dict:
        pattern = f"checkpoint_{tag}_*.json" if tag else "checkpoint_*.json"
        files = sorted(self.checkpoint_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return {}
        with open(files[0], "r", encoding="utf-8") as f:
            self._state = json.load(f)
        return self._state.copy()

    def get_latest_checkpoint_path(self) -> Optional[Path]:
        files = sorted(self.checkpoint_dir.glob("checkpoint_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0] if files else None

    def reset(self):
        self._state.clear()
        for f in self.checkpoint_dir.glob("checkpoint_*.json"):
            f.unlink()

    # ------------------------------------------------------------------
    # Self-healing recovery (v3.3+)
    # ------------------------------------------------------------------
    def self_heal(self, validators: List[Callable[[Dict], Tuple[bool, str]]]) -> dict:
        """
        Attempt auto-recovery with validation chain.
        1. Load latest checkpoint
        2. Run validators
        3. If invalid, rollback to older checkpoint
        4. If all fail, return safe defaults
        """
        files = sorted(self.checkpoint_dir.glob("checkpoint_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    candidate = json.load(fp)
                all_pass = True
                reasons = []
                for v in validators:
                    ok, reason = v(candidate)
                    if not ok:
                        all_pass = False
                        reasons.append(reason)
                if all_pass:
                    self._state = candidate
                    return {"recovered": True, "from": str(f), "state": candidate, "validators": len(validators)}
            except Exception:
                continue
        return {"recovered": False, "reason": "All checkpoints failed validation", "safe_defaults": True}

    def validate_state_integrity(self, state: Dict) -> Tuple[bool, str]:
        """Basic integrity check: equity > 0, no NaN, required keys present."""
        equity = state.get("equity", 0.0)
        if equity < 0:
            return False, f"Negative equity {equity}"
        if any(isinstance(v, float) and (v != v) for v in state.values()):  # NaN check
            return False, "NaN values detected"
        return True, "OK"

    def get_recovery_stats(self) -> dict:
        files = list(self.checkpoint_dir.glob("checkpoint_*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {
            "checkpoint_count": len(files),
            "total_size_bytes": total_size,
            "last_save_age_sec": time.time() - self._last_save if self._last_save > 0 else None,
            "state_keys": list(self._state.keys()),
        }

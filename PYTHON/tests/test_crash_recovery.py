"""
test_crash_recovery.py — Tests for CrashRecoveryManager (K234)
"""
import pytest
import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.crash_recovery import CrashRecoveryManager


class TestCrashRecoveryManager:
    def setup_method(self):
        self.dir = "test_checkpoints"
        if Path(self.dir).exists():
            for f in Path(self.dir).glob("*.json"):
                f.unlink()

    def teardown_method(self):
        if Path(self.dir).exists():
            for f in Path(self.dir).glob("*.json"):
                f.unlink()
            Path(self.dir).rmdir()

    def test_set_and_checkpoint(self):
        mgr = CrashRecoveryManager(checkpoint_dir=self.dir)
        mgr.set("capital", 100000)
        mgr.checkpoint()
        files = list(Path(self.dir).glob("checkpoint_*.json"))
        assert len(files) >= 1

    def test_recover(self):
        mgr = CrashRecoveryManager(checkpoint_dir=self.dir)
        mgr.set("capital", 100000)
        mgr.set("positions", ["THYAO"])
        mgr.checkpoint(tag="test")
        mgr2 = CrashRecoveryManager(checkpoint_dir=self.dir)
        state = mgr2.recover(tag="test")
        assert state.get("capital") == 100000
        assert state.get("positions") == ["THYAO"]

    def test_latest_checkpoint(self):
        mgr = CrashRecoveryManager(checkpoint_dir=self.dir)
        mgr.checkpoint()
        path = mgr.get_latest_checkpoint_path()
        assert path is not None
        assert path.suffix == ".json"

    def test_prune_old(self):
        mgr = CrashRecoveryManager(checkpoint_dir=self.dir, max_checkpoints=2)
        mgr.checkpoint(tag="1")
        mgr.checkpoint(tag="2")
        mgr.checkpoint(tag="3")
        files = list(Path(self.dir).glob("checkpoint_*.json"))
        assert len(files) <= 2

    def test_reset(self):
        mgr = CrashRecoveryManager(checkpoint_dir=self.dir)
        mgr.set("a", 1)
        mgr.checkpoint()
        mgr.reset()
        assert len(list(Path(self.dir).glob("*.json"))) == 0

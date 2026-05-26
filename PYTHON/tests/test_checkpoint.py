"""
Test: PYTHON.agents.checkpoint
Save, load, list, purge.
"""
import pytest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.checkpoint import CheckpointManager


class TestCheckpointManager:
    def test_save_and_load(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            path = mgr.save(state={"agents_state": {"Sinyal": "active"}, "decisions": []}, label="test1")
            assert path.exists()
            data = mgr.load_latest()
            assert data["agents_state"]["Sinyal"] == "active"
            assert data["label"] == "test1"

    def test_load_by_label(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            mgr.save(state={"x": 1}, label="alpha")
            mgr.save(state={"x": 2}, label="beta")
            data = mgr.load_by_label("alpha")
            assert data["x"] == 1

    def test_load_by_label_not_found(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            assert mgr.load_by_label("nonexistent") is None

    def test_list_checkpoints(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            mgr.save(state={"x": 1}, label="a")
            mgr.save(state={"x": 2}, label="b")
            items = mgr.list_checkpoints()
            assert len(items) == 2
            assert all("saved_at" in i for i in items)

    def test_purge_old(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            for i in range(5):
                mgr.save(state={"i": i}, label="purge")
            removed = mgr.purge_old(keep=2)
            assert removed == 3
            assert len(mgr.list_checkpoints()) == 2

    def test_load_latest_empty(self):
        with TemporaryDirectory() as td:
            mgr = CheckpointManager(checkpoint_dir=Path(td))
            assert mgr.load_latest() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
test_persistent_memory.py — Tests for PersistentAgentMemory (K226)
"""
import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.persistent_memory import PersistentAgentMemory, MemoryEntry


class TestPersistentAgentMemory:
    def setup_method(self):
        self.db_path = "test_agent_memory.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_store_and_recall(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        entry = MemoryEntry(agent="Sinyal", category="decision", content="THYAO AL")
        mem_id = mem.store(entry)
        assert mem_id is not None
        rows = mem.recall("Sinyal")
        assert len(rows) == 1
        assert rows[0].content == "THYAO AL"

    def test_recall_by_category(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        mem.store(MemoryEntry(agent="Sinyal", category="decision", content="A"))
        mem.store(MemoryEntry(agent="Sinyal", category="error", content="B"))
        rows = mem.recall("Sinyal", category="error")
        assert len(rows) == 1
        assert rows[0].content == "B"

    def test_recall_limit(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        for i in range(10):
            mem.store(MemoryEntry(agent="Sinyal", category="decision", content=str(i)))
        rows = mem.recall("Sinyal", limit=5)
        assert len(rows) == 5

    def test_stats(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        mem.store(MemoryEntry(agent="Sinyal", category="decision", content="A"))
        mem.store(MemoryEntry(agent="Sinyal", category="error", content="B"))
        stats = mem.get_stats("Sinyal")
        assert stats["total_entries"] == 2
        assert "decision" in stats["categories"]
        assert "error" in stats["categories"]

    def test_forget_old(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        mem.store(MemoryEntry(agent="Sinyal", category="decision", content="old"))
        mem.forget_old("Sinyal", days=0)
        rows = mem.recall("Sinyal")
        assert len(rows) == 0

    def test_reset(self):
        mem = PersistentAgentMemory(db_path=self.db_path)
        mem.store(MemoryEntry(agent="Sinyal", category="decision", content="A"))
        mem.reset()
        stats = mem.get_stats("Sinyal")
        assert stats["total_entries"] == 0

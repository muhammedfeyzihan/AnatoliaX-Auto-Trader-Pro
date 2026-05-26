"""
Test: PYTHON.observability.audit_log
Immutable append-only audit log with hash chain.
"""
import pytest
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from observability.audit_log import ImmutableAuditLog, TamperProofAuditLog


class TestImmutableAuditLog:
    def setup_method(self):
        self.td = tempfile.mkdtemp()
        self.db = Path(self.td) / "audit.db"
        self.audit = ImmutableAuditLog(self.db)

    def teardown_method(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_append_and_query(self):
        h = self.audit.append("ORDER", {"order_id": "1", "symbol": "THYAO"})
        assert isinstance(h, str)
        assert len(h) == 64
        rows = self.audit.query()
        assert len(rows) == 1
        assert rows[0]["event_type"] == "ORDER"

    def test_chain_integrity(self):
        self.audit.append("ORDER", {"id": "1"})
        self.audit.append("ORDER", {"id": "2"})
        assert self.audit.verify_chain() is True

    def test_query_filter_event_type(self):
        self.audit.append("ORDER", {"id": "1"})
        self.audit.append("RISK", {"id": "2"})
        rows = self.audit.query(event_type="ORDER")
        assert len(rows) == 1
        assert rows[0]["event_type"] == "ORDER"

    def test_query_limit(self):
        for i in range(5):
            self.audit.append("ORDER", {"id": str(i)})
        rows = self.audit.query(limit=2)
        assert len(rows) == 2

    def test_stats(self):
        self.audit.append("ORDER", {"id": "1"})
        self.audit.append("RISK", {"id": "2"})
        stats = self.audit.get_stats()
        assert stats["total"] == 2
        assert stats["by_type"]["ORDER"] == 1
        assert stats["by_type"]["RISK"] == 1

    def test_empty_verify(self):
        assert self.audit.verify_chain() is True

    def test_payload_is_json(self):
        self.audit.append("ORDER", {"price": 103.5})
        rows = self.audit.query()
        payload = rows[0]["payload"]
        assert "103.5" in payload


class TestTamperProofAuditLog:
    def setup_method(self):
        self.td = tempfile.mkdtemp()
        self.db = Path(self.td) / "audit_tp.db"
        self.audit = TamperProofAuditLog(self.db, secret="test-secret")

    def teardown_method(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_append_with_secret(self):
        h = self.audit.append("ORDER", {"id": "1"})
        assert len(h) == 64
        assert self.audit.verify_chain() is True

    def test_tamper_detection(self):
        self.audit.append("ORDER", {"id": "1"})
        self.audit.append("ORDER", {"id": "2"})
        # Direkt veritabanina mudahale et (simule)
        import sqlite3
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE audit_log SET payload = '{\"tampered\":true}' WHERE id = 1")
            conn.commit()
        assert self.audit.verify_chain() is False

    def test_different_secrets_different_hashes(self):
        a1 = TamperProofAuditLog(Path(self.td) / "a1.db", secret="s1")
        a2 = TamperProofAuditLog(Path(self.td) / "a2.db", secret="s2")
        h1 = a1.append("ORDER", {"id": "1"})
        h2 = a2.append("ORDER", {"id": "1"})
        assert h1 != h2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

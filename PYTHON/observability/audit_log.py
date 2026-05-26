"""
audit_log.py — Immutable Append-Only Audit Log (SQLite)

Sistemdeki kritik olaylar (emir, risk, kill switch) degistirilemez kayit olarak
SQLite'a yazilir. Hash zinciri ile tutarlilik kontrolu.

Kullanim:
    from observability.audit_log import ImmutableAuditLog
    audit = ImmutableAuditLog("data/audit.db")
    audit.append("ORDER", {"order_id": "123", "symbol": "THYAO", "side": "BUY"})
    audit.append("KILL_SWITCH", {"reason": "Max DD exceeded"})
    audit.verify_chain()  # True/False
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ImmutableAuditLog:
    """
    Degistirilemez audit log.
    Her kayit onceki kayidin hash'ini icerir (linked hash chain).
    """

    TABLE = "audit_log"

    def __init__(self, db_path: str | Path = "data/audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    current_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON {self.TABLE}(timestamp)
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_audit_event
                ON {self.TABLE}(event_type)
                """
            )
            conn.commit()

    def _get_last_hash(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                f"SELECT current_hash FROM {self.TABLE} ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else "0" * 64

    @staticmethod
    def _hash_record(timestamp: str, event_type: str, payload: str, previous_hash: str) -> str:
        data = json.dumps({
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous_hash,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def append(self, event_type: str, payload: dict) -> str:
        """
        Yeni audit kaydi ekle. Returns: kayit hash'i.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        previous_hash = self._get_last_hash()
        current_hash = self._hash_record(timestamp, event_type, payload_str, previous_hash)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO {self.TABLE} (timestamp, event_type, payload, previous_hash, current_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, event_type, payload_str, previous_hash, current_hash),
            )
            conn.commit()
        return current_hash

    def query(
        self,
        event_type: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Audit kayitlarini sorgula. Silme/guncelleme yok (append-only).
        """
        conditions = ["1=1"]
        params: list = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if start:
            conditions.append("timestamp >= ?")
            params.append(start)
        if end:
            conditions.append("timestamp <= ?")
            params.append(end)

        where_clause = " AND ".join(conditions)
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT id, timestamp, event_type, payload, previous_hash, current_hash
                FROM {self.TABLE}
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()

        return [dict(row) for row in rows]

    def verify_chain(self) -> bool:
        """
        Hash zincirinin bozulmamis oldugunu dogrula.
        Her kayidin previous_hash'i bir onceki kayidin current_hash'i ile eslesmeli.
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT id, timestamp, event_type, payload, previous_hash, current_hash
                FROM {self.TABLE}
                ORDER BY id ASC
                """
            ).fetchall()

        if not rows:
            return True

        prev_hash = "0" * 64
        for row in rows:
            _, ts, et, payload, prev_h, curr_h = row
            if prev_h != prev_hash:
                return False
            expected = self._hash_record(ts, et, payload, prev_h)
            if expected != curr_h:
                return False
            prev_hash = curr_h

        return True

    def get_stats(self) -> dict:
        """Toplam kayit sayisi ve olay turu dagilimi."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM {self.TABLE}").fetchone()[0]
            types = conn.execute(
                f"SELECT event_type, COUNT(*) FROM {self.TABLE} GROUP BY event_type"
            ).fetchall()
        return {"total": total, "by_type": {t: c for t, c in types}}


class TamperProofAuditLog(ImmutableAuditLog):
    """
    ImmutableAuditLog + HMAC imza (gizli anahtar ile).
    Daha guclu degistirilemezlik garantisi.
    """

    def __init__(self, db_path: str | Path = "data/audit.db", secret: Optional[str] = None):
        super().__init__(db_path)
        self._secret = (secret or "ANATOLIAX_AUDIT_SECRET").encode("utf-8")

    def _hash_record(self, timestamp: str, event_type: str, payload: str, previous_hash: str) -> str:
        data = json.dumps({
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous_hash,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode("utf-8") + self._secret).hexdigest()


if __name__ == "__main__":
    audit = ImmutableAuditLog("data/audit_demo.db")
    h1 = audit.append("ORDER", {"order_id": "1", "symbol": "THYAO"})
    h2 = audit.append("RISK_EVENT", {"reason": "Max DD"})
    print("Kayit hashleri:", h1, h2)
    print("Zincir dogru mu:", audit.verify_chain())
    print("Stats:", audit.get_stats())
    print("Son 2 kayit:", audit.query(limit=2))

"""
reporting/audit_trail.py — Denetim izi
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class AuditTrail:
    """
    Emir ve islem denetim izi.

    Gereksinimler:
    - SPK/KAP denetim izi standardi
    - Her emirin timsah izi: olusturma, gonderim, onay, iptal, duzeltme
    - Immutable log: silinemez, sadece eklenebilir

    K179: Denetim izi 7 yil saklanir ve SPK denetiminde sunulur.
    """

    def __init__(self, log_dir: str = "DATA/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, payload: Dict) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": payload,
        }
        date_str = datetime.utcnow().strftime("%Y%m%d")
        file_path = self.log_dir / f"audit_{date_str}.ndjson"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

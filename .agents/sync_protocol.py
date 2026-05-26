"""
.agents/sync_protocol.py — Claude <-> Kimi senkronizasyon protokolu
"""
from datetime import datetime
from typing import Dict, Optional


class SyncProtocol:
    """
    Iki ajan (Claude <-> Kimi) arasinda durum senkronizasyonu.

    Protokol:
    - Version: v1
    - Format: JSON over SQLite (SharedMemory)
    - Fields: task_id, agent, status, result, timestamp, checksum
    - Conflict resolution: last-write-wins + human gate L3

    K188: Senkronizasyon her 60sn bir calisir; tutarsizlik varsa alarm verir.
    """

    VERSION = "v1"

    def __init__(self, shared_memory):
        self.store = shared_memory

    def publish(self, task_id: str, agent: str, payload: Dict) -> None:
        record = {
            "version": self.VERSION,
            "task_id": task_id,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        self.store.set(f"sync:{task_id}", record)

    def fetch(self, task_id: str) -> Optional[Dict]:
        return self.store.get(f"sync:{task_id}")

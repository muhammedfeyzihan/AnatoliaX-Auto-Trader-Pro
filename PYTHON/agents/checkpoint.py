"""
checkpoint.py — Ajan konsey toplantisi sonrasi state kaydetme ve crash sonrasi recovery.
tradingagents'tan entegre edilmistir.

Kullanim:
    from agents.checkpoint import CheckpointManager
    mgr = CheckpointManager()
    mgr.save(state={"agents": {...}, "decisions": [...]}, label="konsey_09_30")
    restored = mgr.load_latest()
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import json
import glob
from datetime import datetime
from typing import Optional


DEFAULT_CHECKPOINT_DIR = Path(__file__).resolve().parents[2] / "checkpoints"


class CheckpointManager:
    """
    Her ajan konsey toplantisi sonrasi state'i JSON olarak kaydeder.
    Crash sonrasi son durumdan devam edilebilir.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.dir = checkpoint_dir or DEFAULT_CHECKPOINT_DIR
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: dict, label: Optional[str] = None) -> Path:
        """
        State'i timestamp'li JSON olarak kaydet.

        Args:
            state: agents_state, timestamp, decisions, pending_tasks
            label: Opsiyonel etiket (ornegin 'konsey_09_30')

        Donus: kaydedilen dosya yolu
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ms = datetime.now().strftime("%f")
        name = f"checkpoint_{ts}_{ms}"
        if label:
            name += f"_{label}"
        name += ".json"

        payload = {
            "saved_at": datetime.now().isoformat(),
            "label": label,
            **state,
        }

        path = self.dir / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        return path

    def load_latest(self) -> Optional[dict]:
        """
        En son kaydedilen checkpoint'i yukle.

        Donus: state dict veya None
        """
        pattern = str(self.dir / "checkpoint_*.json")
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            return None
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def load_by_label(self, label: str) -> Optional[dict]:
        """
        Etikete gore checkpoint bul.
        """
        pattern = str(self.dir / f"checkpoint_*_{label}.json")
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            return None
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def list_checkpoints(self) -> list[dict]:
        """
        Tum checkpoint'lerin ozet listesini dondur.
        """
        pattern = str(self.dir / "checkpoint_*.json")
        files = sorted(glob.glob(pattern), reverse=True)
        results = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append({
                    "file": Path(fp).name,
                    "saved_at": data.get("saved_at"),
                    "label": data.get("label"),
                })
            except Exception:
                continue
        return results

    def purge_old(self, keep: int = 10) -> int:
        """
        Eski checkpoint'leri temizle, sadece 'keep' adet tut.

        Donus: silinen dosya sayisi
        """
        pattern = str(self.dir / "checkpoint_*.json")
        files = sorted(glob.glob(pattern), reverse=True)
        removed = 0
        for fp in files[keep:]:
            try:
                Path(fp).unlink()
                removed += 1
            except Exception:
                continue
        return removed


if __name__ == "__main__":
    mgr = CheckpointManager()
    p = mgr.save(
        state={
            "agents_state": {"Sinyal": "active", "Risk": "active", "Strateji": "active"},
            "decisions": [{"symbol": "THYAO", "verdict": "ONAY"}],
            "pending_tasks": [],
        },
        label="demo",
    )
    print("Checkpoint saved:", p)
    print("Latest:", mgr.load_latest())
    print("List:", mgr.list_checkpoints())

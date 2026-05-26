"""
mlops/model_registry.py — Model versiyonlama ve kayit
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class ModelRegistry:
    """
    ML model registry.

    Ozellikler:
    - Semantic versioning (MAJOR.MINOR.PATCH)
    - Metadata: egitim tarihi, veri araligi, metrikler
    - ONNX/Checkpoint saklama
    - Rollback destegi

    K196: Her model deployment oncesi registry'e kaydedilir.
    """

    def __init__(self, registry_dir: str = "DATA/models"):
        self.dir = Path(registry_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def register(self, name: str, version: str, path: str, metrics: Dict) -> None:
        meta = {
            "name": name,
            "version": version,
            "path": path,
            "metrics": metrics,
            "registered_at": datetime.utcnow().isoformat(),
        }
        meta_path = self.dir / f"{name}_{version}.json"
        import json
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def get_latest(self, name: str) -> Optional[Dict]:
        files = sorted(self.dir.glob(f"{name}_*.json"))
        if not files:
            return None
        import json
        return json.loads(files[-1].read_text(encoding="utf-8"))

"""
.agents/knowledge_base.py — Ajan bilgi bankasi (RAG)
"""
from pathlib import Path
from typing import List, Dict


class KnowledgeBase:
    """
    Ajanlarin paylastigi bilgi bankasi.

    Kaynaklar:
    - KURALLAR/*.md
    - STRATEJILER/*.md
    - AJANLAR/*.md
    - Kod docstring'leri
    - Hata kayitlari

    K189: Bilgi bankasi ChromaDB ile vektorlestirilir; benzerlik aramasi yapilir.
    """

    def __init__(self, root: str = ".", embedder=None):
        self.root = Path(root)
        self.embedder = embedder
        self._docs: List[str] = []

    def index_rules(self) -> None:
        for path in (self.root / "KURALLAR").rglob("*.md"):
            self._docs.append(path.read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        # Basit keyword aramasi (ChromaDB entegrasyonu sonraki asama)
        results = []
        for doc in self._docs:
            if query.lower() in doc.lower():
                results.append({"content": doc[:500], "score": 1.0})
        return results[:top_k]

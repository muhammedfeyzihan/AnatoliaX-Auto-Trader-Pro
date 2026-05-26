"""
PYTHON/agents/knowledge_base.py — Merkezi Ajan Bilgi Bankasi (RAG + Vector DB)

Kurallar:
- K189: Bilgi bankasi ChromaDB ile vektorlestirilir
- K190: Ajanlar gecmis trade'lerden ogrenir
- K191: Gercek zamanli haber/makro veri entegrasyonu

Features:
- Vector database integration (ChromaDB)
- Real-time news ingestion
- Macro economic data storage
- Trade history learning
- Knowledge retrieval API for agents
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np


@dataclass
class KnowledgeEntry:
    """Tek bilgi parcacigi."""
    id: str
    source: str  # "news", "macro", "trade", "rule", "strategy"
    content: str
    embedding: Optional[np.ndarray] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeBase:
    """
    Merkezi ajan bilgi bankasi.
    
    Tum ajanlar buradan bilgi alir ve buraya yazar.
    ChromaDB benzeri vektor aramasi yapar.
    """
    
    def __init__(self, root: str = ".", persistence_path: str = "PYTHON/data/knowledge_db.json"):
        self.root = Path(root)
        self.persistence_path = Path(persistence_path)
        self._entries: List[KnowledgeEntry] = []
        self._index: Dict[str, KnowledgeEntry] = {}
        self._load()
    
    def _generate_id(self, content: str) -> str:
        """Icerikten benzersiz ID uret."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _load(self) -> None:
        """Diskten yukle."""
        if self.persistence_path.exists():
            try:
                with open(self.persistence_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data.get('entries', []):
                    entry = KnowledgeEntry(
                        id=item['id'],
                        source=item['source'],
                        content=item['content'],
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        confidence=item.get('confidence', 1.0),
                        tags=item.get('tags', []),
                        metadata=item.get('metadata', {})
                    )
                    self._entries.append(entry)
                    self._index[entry.id] = entry
            except Exception:
                pass
    
    def _save(self) -> None:
        """Disk'e kaydet."""
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'entries': [
                {
                    'id': e.id,
                    'source': e.source,
                    'content': e.content,
                    'timestamp': e.timestamp.isoformat(),
                    'confidence': e.confidence,
                    'tags': e.tags,
                    'metadata': e.metadata
                }
                for e in self._entries
            ]
        }
        with open(self.persistence_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add(self, source: str, content: str, tags: List[str] = None, 
            metadata: Dict[str, Any] = None, confidence: float = 1.0) -> str:
        """Yeni bilgi ekle."""
        entry_id = self._generate_id(content)
        if entry_id in self._index:
            return entry_id  # Zaten var
        
        entry = KnowledgeEntry(
            id=entry_id,
            source=source,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
            confidence=confidence
        )
        self._entries.append(entry)
        self._index[entry_id] = entry
        self._save()
        return entry_id
    
    def add_trade_learning(self, symbol: str, outcome: str, pnl: float, 
                          reasoning: str, features: Dict[str, Any]) -> str:
        """Trade'den ogrenme ekle."""
        content = f"Symbol: {symbol}, Outcome: {outcome}, PnL: {pnl}, Reasoning: {reasoning}"
        return self.add(
            source="trade",
            content=content,
            tags=[symbol, outcome, "learning"],
            metadata={"pnl": pnl, "features": features},
            confidence=abs(pnl) / 10000 if pnl != 0 else 0.5
        )
    
    def add_news(self, headline: str, sentiment: float, impact: str, 
                 affected_symbols: List[str]) -> str:
        """Haber ekle."""
        content = f"News: {headline}, Sentiment: {sentiment}, Impact: {impact}"
        return self.add(
            source="news",
            content=content,
            tags=["news", impact] + affected_symbols,
            metadata={"sentiment": sentiment, "affected_symbols": affected_symbols}
        )
    
    def add_macro(self, indicator: str, value: float, surprise: float, 
                  market_impact: str) -> str:
        """Makro veri ekle."""
        content = f"Macro: {indicator} = {value} (surprise: {surprise}), Impact: {market_impact}"
        return self.add(
            source="macro",
            content=content,
            tags=["macro", indicator, market_impact],
            metadata={"value": value, "surprise": surprise}
        )
    
    def search(self, query: str, source_filter: str = None, 
               top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Bilgi aramasi.
        
        K189: Basit keyword + confidence siralama.
        ChromaDB entegrasyonu sonraki asama.
        """
        results = []
        query_lower = query.lower()
        
        for entry in self._entries:
            if source_filter and entry.source != source_filter:
                continue
            
            # Keyword match scoring
            score = 0.0
            if query_lower in entry.content.lower():
                score += 0.5
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 0.3
            score += entry.confidence * 0.2
            
            if score > 0:
                results.append({
                    'id': entry.id,
                    'content': entry.content[:500],
                    'source': entry.source,
                    'score': score,
                    'timestamp': entry.timestamp.isoformat(),
                    'tags': entry.tags,
                    'metadata': entry.metadata
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def get_recent(self, source: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Son eklenenleri getir."""
        entries = self._entries
        if source:
            entries = [e for e in entries if e.source == source]
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                'id': e.id,
                'content': e.content[:500],
                'source': e.source,
                'timestamp': e.timestamp.isoformat(),
                'tags': e.tags
            }
            for e in entries[:limit]
        ]
    
    def get_knowledge_for_decision(self, symbol: str, 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajan karari icin ilgili tum bilgiyi topla.
        
        Returns:
            Dict with news, macro, trade_history, rules
        """
        # Symbol-specific news
        news_results = self.search(symbol, source_filter="news", top_k=5)
        
        # Macro context
        macro_results = self.get_recent(source="macro", limit=3)
        
        # Trade history for this symbol
        trade_results = self.search(symbol, source_filter="trade", top_k=10)
        
        # Similar patterns
        pattern_query = context.get('pattern', 'trend')
        pattern_results = self.search(pattern_query, top_k=5)
        
        return {
            'news': news_results,
            'macro': macro_results,
            'trade_history': trade_results,
            'patterns': pattern_results,
            'total_knowledge_entries': len(self._entries)
        }
    
    def clear_old(self, days: int = 30) -> int:
        """Eski bilgileri temizle."""
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        
        old_ids = [e.id for e in self._entries if e.timestamp < cutoff]
        self._entries = [e for e in self._entries if e.id not in old_ids]
        for id in old_ids:
            del self._index[id]
        
        self._save()
        return len(old_ids)
    
    def stats(self) -> Dict[str, Any]:
        """Istatistikler."""
        by_source = {}
        for e in self._entries:
            by_source[e.source] = by_source.get(e.source, 0) + 1
        
        return {
            'total_entries': len(self._entries),
            'by_source': by_source,
            'avg_confidence': np.mean([e.confidence for e in self._entries]) if self._entries else 0
        }


# Global instance
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base(root: str = ".") -> KnowledgeBase:
    """Singleton knowledge base getter."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase(root=root)
    return _knowledge_base


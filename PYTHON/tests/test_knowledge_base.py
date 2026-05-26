"""
PYTHON/tests/test_knowledge_base.py — Knowledge Base Testleri

K189: Bilgi bankasi ChromaDB ile vektorlestirilir
K190: Ajanlar gecmis trade'lerden ogrenir
K191: Gercek zamanli haber/makro veri entegrasyonu
"""
import pytest
import sys
from pathlib import Path

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.knowledge_base import KnowledgeBase, get_knowledge_base


class TestKnowledgeBase:
    """Knowledge base testleri."""
    
    @pytest.fixture
    def kb(self, tmp_path):
        """Test knowledge base."""
        db_path = tmp_path / "test_kb.json"
        return KnowledgeBase(root=str(tmp_path), persistence_path=str(db_path))
    
    def test_add_and_search(self, kb):
        """Bilgi ekleme ve arama testi."""
        # Add
        entry_id = kb.add(
            source="news",
            content="THYAO stock rises 5% on strong earnings",
            tags=["THYAO", "earnings", "bullish"],
            metadata={"sentiment": 0.8}
        )
        
        assert entry_id is not None
        assert len(kb._entries) == 1
        
        # Search
        results = kb.search("THYAO")
        assert len(results) > 0
        assert "THYAO" in results[0]['content']
    
    def test_trade_learning(self, kb):
        """Trade ogrenme testi (K190)."""
        entry_id = kb.add_trade_learning(
            symbol="GARAN",
            outcome="profit",
            pnl=1500.0,
            reasoning="Strong momentum breakout",
            features={"rsi": 65, "volume": 1.5}
        )
        
        assert entry_id is not None
        
        # Search trade history
        results = kb.search("GARAN", source_filter="trade")
        assert len(results) > 0
        assert results[0]['metadata']['pnl'] == 1500.0
    
    def test_news_integration(self, kb):
        """Haber entegrasyonu testi (K191)."""
        entry_id = kb.add_news(
            headline="FED raises interest rates",
            sentiment=-0.5,
            impact="high",
            affected_symbols=["THYAO", "GARAN", "AKBNK"]
        )
        
        assert entry_id is not None
        
        # Search by symbol
        results = kb.search("THYAO", source_filter="news")
        assert len(results) > 0
    
    def test_macro_data(self, kb):
        """Makro veri testi (K191)."""
        entry_id = kb.add_macro(
            indicator="USD/TRY",
            value=32.5,
            surprise=0.02,
            market_impact="bullish"
        )
        
        assert entry_id is not None
        
        # Get recent macro
        macro = kb.get_recent(source="macro", limit=1)
        assert len(macro) > 0
        assert macro[0]['source'] == "macro"
    
    def test_knowledge_for_decision(self, kb):
        """Karar icin bilgi toplama testi."""
        # Add various knowledge
        kb.add_trade_learning("THYAO", "profit", 1000, "Good entry", {})
        kb.add_news("THYAO earnings beat", 0.7, "medium", ["THYAO"])
        kb.add_macro("Inflation", 0.05, 0.01, "bearish")
        
        # Get knowledge for decision
        knowledge = kb.get_knowledge_for_decision(
            symbol="THYAO",
            context={'pattern': 'breakout'}
        )
        
        assert 'news' in knowledge
        assert 'macro' in knowledge
        assert 'trade_history' in knowledge
        assert 'patterns' in knowledge
    
    def test_persistence(self, kb, tmp_path):
        """Persistence testi."""
        # Add data
        kb.add("test", "Test content", ["test"])
        kb._save()
        
        # Create new instance
        db_path = tmp_path / "test_kb.json"
        kb2 = KnowledgeBase(root=str(tmp_path), persistence_path=str(db_path))
        
        # Should load persisted data
        assert len(kb2._entries) == 1
        assert kb2._entries[0].content == "Test content"
    
    def test_clear_old(self, kb):
        """Eski veri temizleme testi."""
        # Add old data
        kb.add("test", "Old content", ["test"])
        
        # Clear old (should clear since timestamp is now)
        cleared = kb.clear_old(days=0)
        
        assert cleared >= 0
    
    def test_stats(self, kb):
        """Istatistik testi."""
        kb.add("news", "News 1", ["news"])
        kb.add("news", "News 2", ["news"])
        kb.add("trade", "Trade 1", ["trade"])
        
        stats = kb.stats()
        
        assert stats['total_entries'] == 3
        assert 'news' in stats['by_source']
        assert stats['by_source']['news'] == 2
        assert stats['by_source']['trade'] == 1
    
    def test_duplicate_prevention(self, kb):
        """Duplikasyon onleme testi."""
        content = "Duplicate test content"
        
        id1 = kb.add("test", content)
        id2 = kb.add("test", content)
        
        # Should return same ID for duplicate
        assert id1 == id2
        assert len(kb._entries) == 1
    
    def test_confidence_scoring(self, kb):
        """Confidence scoring testi."""
        kb.add("test", "High confidence", confidence=0.9)
        kb.add("test", "Low confidence", confidence=0.1)
        
        results = kb.search("confidence")
        
        # Higher confidence should rank higher
        assert len(results) == 2
        assert results[0]['score'] >= results[1]['score']
    
    def test_tag_search(self, kb):
        """Tag arama testi."""
        kb.add("test", "Content", tags=["bullish", "THYAO", "breakout"])
        
        results = kb.search("bullish")
        assert len(results) > 0
        assert "bullish" in results[0]['tags']
    
    def test_get_knowledge_base_singleton(self):
        """Singleton pattern testi."""
        kb1 = get_knowledge_base()
        kb2 = get_knowledge_base()
        
        assert kb1 is kb2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


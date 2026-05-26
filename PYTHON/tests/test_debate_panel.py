"""
Test: PYTHON.agents.debate_panel
Bull/Bear tartisma, consensus skoru, risk etiketi.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.debate_panel import DebatePanel


class TestDebatePanel:
    def test_init(self):
        panel = DebatePanel(symbol="THYAO")
        assert panel.symbol == "THYAO"

    def test_bull_strong_consensus(self):
        panel = DebatePanel(symbol="THYAO")
        result = panel.debate(
            bull_args={"teknik": "AL", "haber": "pozitif", "ps": 85, "risk": "UYGUN", "makro": "BOGA"},
            bear_args={"teknik": "SAT", "haber": "notr", "ps": 35, "risk": "UYGUN", "makro": "YAN"},
        )
        assert result["consensus_score"] >= 70
        assert result["tavsiye"] == "AL"
        assert result["risk_etiketi"] == "UYGUN"
        assert len(result["transcript"]) == 4

    def test_bear_strong_consensus(self):
        panel = DebatePanel(symbol="THYAO")
        result = panel.debate(
            bull_args={"teknik": "AL", "haber": "notr", "ps": 35, "risk": "RED", "makro": "AYI"},
            bear_args={"teknik": "SAT", "haber": "negatif", "ps": 20, "risk": "RED", "makro": "AYI"},
        )
        assert result["consensus_score"] < 45
        assert result["tavsiye"] == "PASS"
        assert result["risk_etiketi"] == "RED"

    def test_neutral_consensus(self):
        panel = DebatePanel(symbol="THYAO")
        result = panel.debate(
            bull_args={"teknik": "AL", "haber": "notr", "ps": 55, "risk": "UYGUN", "makro": "YAN"},
            bear_args={"teknik": "SAT", "haber": "notr", "ps": 50, "risk": "SINIRLI", "makro": "YAN"},
        )
        assert 45 <= result["consensus_score"] < 70
        assert result["tavsiye"] == "IZLE"

    def test_quick_debate(self):
        result = DebatePanel.quick_debate(
            symbol="GARAN",
            bull={"teknik": "AL", "haber": "pozitif", "ps": 90, "risk": "UYGUN", "makro": "BOGA"},
            bear={"teknik": "SAT", "haber": "negatif", "ps": 10, "risk": "RED", "makro": "AYI"},
        )
        assert "consensus_score" in result
        assert "tavsiye" in result

    def test_gerekce_contains_fields(self):
        panel = DebatePanel(symbol="THYAO")
        result = panel.debate(
            bull_args={"teknik": "AL", "haber": "pozitif", "ps": 85, "risk": "UYGUN", "makro": "BOGA"},
            bear_args={"teknik": "SAT", "haber": "notr", "ps": 35, "risk": "UYGUN", "makro": "YAN"},
        )
        g = result["gerekce"]
        assert "Consensus" in g
        assert "Tavsiye" in g


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test: PYTHON.data.macro_fetcher
MacroFetcher makro veri cekme (mock HTTP).
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.macro_fetcher import MacroFetcher


class TestMacroFetcher:
    def test_init(self):
        mf = MacroFetcher()
        assert mf is not None

    @patch("data.macro_fetcher.requests.Session.get")
    def test_fetch_usdtry(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"rates": {"TRY": 32.5}},
        )
        mf = MacroFetcher()
        result = mf.fetch_usdtry()
        assert result["value"] == 32.5
        assert result["indicator"] == "USDTRY"

    @patch("data.macro_fetcher.requests.Session.get")
    def test_fetch_usdtry_failure(self, mock_get):
        mock_get.side_effect = Exception("Timeout")
        mf = MacroFetcher()
        result = mf.fetch_usdtry()
        assert result["value"] == 0.0
        assert "error" in result

    def test_fetch_bist100(self):
        mf = MacroFetcher()
        result = mf.fetch_bist100()
        assert result["indicator"] == "BIST100"

    def test_get_regime_score(self):
        mf = MacroFetcher()
        with patch.object(mf, "fetch_usdtry", return_value={"indicator":"USDTRY","value":28.0,"timestamp":""}), \
             patch.object(mf, "fetch_bist100", return_value={"indicator":"BIST100","value":10500.0,"timestamp":""}), \
             patch.object(mf, "fetch_vix", return_value={"indicator":"VIX","value":18.0,"timestamp":""}), \
             patch.object(mf, "fetch_gold", return_value={"indicator":"GOLD","value":2000.0,"timestamp":""}), \
             patch.object(mf, "fetch_dxy", return_value={"indicator":"DXY","value":105.0,"timestamp":""}), \
             patch.object(mf, "fetch_brent", return_value={"indicator":"BRENT","value":80.0,"timestamp":""}), \
             patch.object(mf, "fetch_tcmb_rate", return_value={"indicator":"TCMB_RATE","value":50.0,"timestamp":""}), \
             patch.object(mf, "fetch_inflation", return_value={"indicator":"TUFe","value":0.0,"timestamp":""}):
            regime = mf.get_regime_score()
            assert "regime" in regime
            assert "score" in regime
            assert isinstance(regime["score"], int)

    def test_get_regime_score_failure(self):
        mf = MacroFetcher()
        # VIX > 25 (stresli), USD/TRY > 30 (yukselen), BIST100 dusuk -> BEAR
        with patch.object(mf, "fetch_usdtry", return_value={"indicator":"USDTRY","value":35.0,"timestamp":""}), \
             patch.object(mf, "fetch_bist100", return_value={"indicator":"BIST100","value":8000.0,"timestamp":""}), \
             patch.object(mf, "fetch_vix", return_value={"indicator":"VIX","value":30.0,"timestamp":""}), \
             patch.object(mf, "fetch_gold", return_value={"indicator":"GOLD","value":2000.0,"timestamp":""}), \
             patch.object(mf, "fetch_dxy", return_value={"indicator":"DXY","value":105.0,"timestamp":""}), \
             patch.object(mf, "fetch_brent", return_value={"indicator":"BRENT","value":80.0,"timestamp":""}), \
             patch.object(mf, "fetch_tcmb_rate", return_value={"indicator":"TCMB_RATE","value":50.0,"timestamp":""}), \
             patch.object(mf, "fetch_inflation", return_value={"indicator":"TUFe","value":0.0,"timestamp":""}):
            regime = mf.get_regime_score()
            assert regime["regime"] == "BEAR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

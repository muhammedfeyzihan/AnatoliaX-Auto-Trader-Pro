"""
test_ai_regime_detector.py — Tests for AIRegimeDetector (K227)
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.ai_regime_detector import AIRegimeDetector


class TestAIRegimeDetector:
    def test_bull_detection(self):
        det = AIRegimeDetector(lookback=20)
        # Uptrend with larger oscillation (vol ~0.2)
        close = 100 + np.linspace(0, 200, 100) + 30 * np.sin(np.linspace(0, 4 * np.pi, 100))
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        result = det.predict(df)
        assert result.regime == "bull"
        assert result.confidence > 0.5
        assert "trend" in result.features

    def test_bear_detection(self):
        det = AIRegimeDetector(lookback=20)
        # Downtrend with larger oscillation (vol ~0.2)
        close = 300 - np.linspace(0, 200, 100) + 30 * np.sin(np.linspace(0, 4 * np.pi, 100))
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        result = det.predict(df)
        assert result.regime == "bear"
        assert result.confidence > 0.5

    def test_volatile_detection(self):
        det = AIRegimeDetector(lookback=20)
        # Heavy oscillation (vol > 0.5)
        close = 100 + 50 * np.sin(np.linspace(0, 20 * np.pi, 100))
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        result = det.predict(df)
        assert result.regime == "volatile"

    def test_low_vol_detection(self):
        det = AIRegimeDetector(lookback=20)
        # Almost flat line (vol < 0.1)
        close = 100 + np.linspace(0, 1, 100)
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        result = det.predict(df)
        assert result.regime == "low_vol"

    def test_short_data_returns_unknown(self):
        det = AIRegimeDetector(lookback=50)
        df = pd.DataFrame({"close": [100, 101], "high": [101, 102], "low": [99, 100]})
        result = det.predict(df)
        assert result.regime == "unknown"

    def test_fit_predict(self):
        det = AIRegimeDetector(lookback=20)
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        det.fit(df)
        result = det.predict(df)
        assert result.regime in det.REGIMES

    def test_history(self):
        det = AIRegimeDetector(lookback=20)
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        det.predict(df)
        hist = det.get_regime_history()
        assert len(hist) >= 1

    def test_summary(self):
        det = AIRegimeDetector(lookback=20)
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)
        df = pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})
        det.predict(df)
        summary = det.get_summary()
        assert isinstance(summary, dict)
        assert sum(summary.values()) == pytest.approx(1.0, abs=0.01)

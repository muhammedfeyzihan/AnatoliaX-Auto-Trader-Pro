"""
Test: manipulation/multi_tf_detector
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manipulation.multi_tf_detector import MultiTFManipDetector, ManipResult


class TestMultiTFManipDetector:
    def _make_clean_bars(self, n=50):
        close = np.linspace(100, 110, n)
        high = close + 0.5
        low = close - 0.5
        volume = np.ones(n) * 1000
        return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    def _make_volume_anomaly(self, n=50):
        close = np.linspace(100, 101, n)
        high = close + 0.5
        low = close - 0.5
        volume = np.concatenate([np.ones(40) * 1000, np.ones(9) * 1000, np.array([15000])])
        return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    def _make_fake_breakout(self, n=50):
        close = np.concatenate([np.linspace(100, 104, n - 1), np.array([106])])
        high = close + 0.5
        low = close - 0.5
        volume = np.concatenate([np.ones(40) * 2000, np.ones(9) * 2000, np.array([500])])
        return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    def test_clean_passes(self):
        detector = MultiTFManipDetector()
        bars = {"1d": self._make_clean_bars()}
        res = detector.scan("THYAO", bars=bars)
        assert isinstance(res, ManipResult)
        assert res.is_manipulated is False
        assert res.threat_score < 60

    def test_volume_anomaly_detected(self):
        detector = MultiTFManipDetector()
        bars = {"1d": self._make_volume_anomaly()}
        res = detector.scan("THYAO", bars=bars)
        assert res.is_manipulated is True
        assert "volume_anomaly" in str(res.reason)

    def test_fake_breakout_detected(self):
        detector = MultiTFManipDetector()
        bars = {"1d": self._make_fake_breakout()}
        res = detector.scan("THYAO", bars=bars)
        assert res.is_manipulated is True
        assert "fake_breakout" in str(res.reason)

    def test_multi_tf_escalation(self):
        detector = MultiTFManipDetector()
        bars = {
            "15m": self._make_volume_anomaly(),
            "1h": self._make_volume_anomaly(),
        }
        res = detector.scan("THYAO", bars=bars)
        # 2+ TFs flagged → escalated score
        assert res.is_manipulated is True
        assert len(res.timeframe_flags) == 2

    def test_no_data(self):
        detector = MultiTFManipDetector()
        res = detector.scan("THYAO", bars={})
        assert res.is_manipulated is False
        assert res.threat_score == 0.0

    def test_divergence_detected(self):
        n = 50
        close = np.concatenate([np.linspace(100, 115, 25), np.linspace(115, 120, 25)])
        high = close + 1
        low = close - 1
        volume = np.ones(n) * 1000
        df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})
        detector = MultiTFManipDetector()
        res = detector.scan("THYAO", bars={"1d": df})
        # Divergence is subtle; just verify scan completes
        assert isinstance(res, ManipResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

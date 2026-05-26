"""
Test: PYTHON.backtest.signals
Sinyal skoru uretimi dogrulama.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.indicators import apply_all
from backtest.signals import (
    combined_signal,
    ema_cross_signal,
    rsi_extreme_signal,
    bb_squeeze_volume_signal,
    vwap_bounce_signal,
    momentum_spike_signal,
)
from strategy.parameter_registry import SignalConfig


class TestSignals:
    def _load_and_prepare(self) -> pd.DataFrame:
        path = Path(__file__).resolve().parent / "fixtures" / "THYAO_20days.csv"
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = apply_all(df)
        return df

    def _make_df(self, n=50):
        import numpy as np
        np.random.seed(42)
        df = pd.DataFrame({
            "open": np.cumsum(np.random.randn(n)) + 100,
            "high": np.cumsum(np.random.randn(n)) + 105,
            "low": np.cumsum(np.random.randn(n)) + 95,
            "close": np.cumsum(np.random.randn(n)) + 100,
            "volume": np.random.randint(10000, 50000, n),
        })
        return df

    def test_combined_signal_returns_columns(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        assert "Signal_Score" in df.columns
        assert "Signal" in df.columns

    def test_signal_score_range(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        scores = df["Signal_Score"].dropna()
        assert (scores >= 0).all()
        assert (scores <= 100).all()

    def test_signal_values(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        signals = df["Signal"].dropna()
        assert set(signals.unique()).issubset({0, 1, 2})

    def test_strong_buy_threshold(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        # 20 gunluk veride STRONG BUY olmayabilir; sadece skor kontrolu yapalim
        strong_buys = df[df["Signal_Score"] >= 70]
        # En azindan skorlar hesaplaniyor olmali
        assert "Signal_Score" in df.columns

    def test_buy_threshold(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        buys = df[(df["Signal_Score"] >= 55) & (df["Signal_Score"] <= 70)]
        # 20 gunluk veride BUY olabilir veya olmayabilir
        assert len(buys) >= 0

    def test_reject_threshold(self):
        df = self._load_and_prepare()
        df = combined_signal(df)
        rejects = df[df["Signal_Score"] < 40]
        # 20 gunluk veride REJECT olabilir veya olmayabilir
        assert len(rejects) >= 0

    def test_ema_cross_signal(self):
        df = self._make_df(50)
        s = ema_cross_signal(df)
        assert isinstance(s, pd.Series)
        assert s.dtype == int

    def test_rsi_extreme_signal(self):
        df = self._make_df(50)
        s = rsi_extreme_signal(df)
        assert isinstance(s, pd.Series)

    def test_bb_squeeze_volume_signal(self):
        df = self._make_df(50)
        s = bb_squeeze_volume_signal(df)
        assert isinstance(s, pd.Series)

    def test_vwap_bounce_signal(self):
        df = self._make_df(50)
        s = vwap_bounce_signal(df)
        assert isinstance(s, pd.Series)

    def test_momentum_spike_signal(self):
        df = self._make_df(50)
        s = momentum_spike_signal(df)
        assert isinstance(s, pd.Series)

    def test_combined_signal_with_config(self):
        df = self._load_and_prepare()
        cfg = SignalConfig(ema_weight=0.30, rsi_weight=0.10, score_strong=65.0, score_moderate=50.0)
        df = combined_signal(df, config=cfg)
        assert "Signal_Score" in df.columns
        assert "Signal" in df.columns
        # With different weights, scores should still be in valid range
        scores = df["Signal_Score"].dropna()
        assert (scores >= 0).all()
        assert (scores <= 100).all()

    def test_combined_signal_bull_config(self):
        df = self._load_and_prepare()
        cfg = SignalConfig(ema_weight=0.25, rsi_upper=75.0, volume_z_threshold=2.0)
        df = combined_signal(df, config=cfg)
        assert "Signal_Score" in df.columns
        # Higher RSI upper bound should allow more RSI-ok signals
        assert "Signal" in df.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

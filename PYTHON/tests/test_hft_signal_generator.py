"""
Test: PYTHON.hft.signal_generator
M1 momentum and S1 micro-scalp signals.
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hft.signal_generator import m1_momentum_signal, s1_micro_scalp_signal, generate_signal_from_df


class TestSignalGenerator:
    def _make_prices_volumes(self, n=50):
        np.random.seed(42)
        prices = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
        volumes = 1000 + np.random.randint(0, 500, n)
        volumes[-1] = 5000  # volume spike
        return prices, volumes

    def test_m1_momentum_no_signal_on_flat(self):
        prices = np.ones(50) * 100.0
        volumes = np.ones(50) * 1000
        sig = m1_momentum_signal(prices, volumes)
        assert sig == 0

    def test_m1_momentum_buy_on_cross(self):
        # EMA3 dips below EMA8 then surges above with volume spike
        prices = np.ones(50) * 100.0
        prices[-3] = 99.0
        prices[-2] = 100.0
        prices[-1] = 115.0
        volumes = np.ones(50) * 1000
        volumes[-1] = 5000
        sig = m1_momentum_signal(prices, volumes)
        assert sig == 1

    def test_m1_momentum_sell_on_cross(self):
        # EMA3 rises above EMA8 then crashes below with volume spike
        prices = np.ones(50) * 100.0
        prices[-3] = 101.0
        prices[-2] = 100.0
        prices[-1] = 85.0
        volumes = np.ones(50) * 1000
        volumes[-1] = 5000
        sig = m1_momentum_signal(prices, volumes)
        assert sig == -1

    def test_s1_micro_scalp_no_signal_on_flat(self):
        prices = np.ones(50) * 100.0
        volumes = np.ones(50) * 1000
        sig = s1_micro_scalp_signal(prices, volumes)
        assert sig == 0

    def test_generate_signal_from_df(self):
        prices = np.ones(50) * 100.0
        prices[-3] = 99.0
        prices[-2] = 100.0
        prices[-1] = 115.0
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-05-21", periods=50, freq="min"),
            "close": prices,
            "volume": [1000] * 49 + [5000],
        })
        sig = generate_signal_from_df(df, strategy="m1_momentum")
        assert sig is not None
        assert sig["signal"] == 1
        assert "entry" in sig

    def test_generate_signal_from_df_none_on_short(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-05-21", periods=10, freq="min"),
            "close": [100.0] * 10,
            "volume": [100] * 10,
        })
        sig = generate_signal_from_df(df, strategy="m1_momentum")
        assert sig is None

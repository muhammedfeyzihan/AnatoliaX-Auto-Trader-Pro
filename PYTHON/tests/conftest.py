"""
PYTHON/tests/conftest.py — Pytest Configuration and Common Fixtures

Provides common imports and fixtures for all tests.
"""
import sys
import os
from pathlib import Path

# Add PYTHON to path
PYTHON_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PYTHON_DIR))

# Common imports available to all tests
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
import pytest

# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )

@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory."""
    return PYTHON_DIR / "tests" / "data"

@pytest.fixture(scope="session")
def sample_timestamp():
    """Sample timestamp for tests."""
    return datetime.now(timezone.utc)

@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV DataFrame for testing."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    return pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 101,
        'volume': np.random.randint(1000, 10000, 100)
    })

@pytest.fixture
def sample_tick_data():
    """Sample tick data for testing."""
    return [
        {"price": 100.0, "volume": 100, "timestamp": datetime.now(timezone.utc)},
        {"price": 100.5, "volume": 150, "timestamp": datetime.now(timezone.utc)},
        {"price": 101.0, "volume": 200, "timestamp": datetime.now(timezone.utc)},
    ]


"""
Test: PYTHON.common.validators
NaN/Inf rejection, DataFrame validation, event dict validation.
"""
import pytest
import math
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.validators import (
    validate_no_nan_inf,
    validate_price,
    validate_quantity,
    validate_dataframe,
    validate_event_dict,
    ValidationError,
)


class TestValidators:
    def test_validate_no_nan_inf_ok(self):
        assert validate_no_nan_inf(100.0) == 100.0

    def test_validate_no_nan_inf_rejects_nan(self):
        with pytest.raises(ValidationError, match="NaN"):
            validate_no_nan_inf(float("nan"))

    def test_validate_no_nan_inf_rejects_inf(self):
        with pytest.raises(ValidationError, match="Inf"):
            validate_no_nan_inf(float("inf"))

    def test_validate_price_bounds(self):
        with pytest.raises(ValidationError, match="minimum"):
            validate_price(-1.0)
        with pytest.raises(ValidationError, match="maximum"):
            validate_price(2_000_000.0)

    def test_validate_quantity_positive(self):
        with pytest.raises(ValidationError, match="must be > 0"):
            validate_quantity(0.0)
        with pytest.raises(ValidationError, match="must be > 0"):
            validate_quantity(-5.0)

    def test_validate_dataframe_required_cols(self):
        df = pd.DataFrame({"timestamp": [1, 2], "close": [100, 101]})
        result = validate_dataframe(df, required_cols=["timestamp", "close"])
        assert result is df

    def test_validate_dataframe_missing_cols(self):
        df = pd.DataFrame({"timestamp": [1, 2]})
        with pytest.raises(ValidationError, match="Missing required"):
            validate_dataframe(df, required_cols=["timestamp", "close"])

    def test_validate_dataframe_rejects_nan(self):
        df = pd.DataFrame({"close": [100.0, np.nan]})
        with pytest.raises(ValidationError, match="NaN"):
            validate_dataframe(df)

    def test_validate_dataframe_rejects_inf(self):
        df = pd.DataFrame({"close": [100.0, np.inf]})
        with pytest.raises(ValidationError, match="Inf"):
            validate_dataframe(df)

    def test_validate_dataframe_empty_raises(self):
        with pytest.raises(ValidationError, match="empty"):
            validate_dataframe(pd.DataFrame())

    def test_validate_event_dict_ok(self):
        d = {"price": 100.0, "qty": 50}
        assert validate_event_dict(d) == d

    def test_validate_event_dict_rejects_nan(self):
        with pytest.raises(ValidationError, match="NaN"):
            validate_event_dict({"price": float("nan")})

    def test_validate_event_dict_nested(self):
        with pytest.raises(ValidationError, match="NaN"):
            validate_event_dict({"meta": {"value": float("nan")}})

"""
validators.py — NaN/Inf validation layer for market data and execution events.
Inspired by Nautilus Trader's strict deserialization rules.
"""

import math
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class ValidationError(ValueError):
    """Raised when a value fails validation."""
    pass


def validate_no_nan_inf(value: float, name: str = "value") -> float:
    """Reject NaN or Inf floats."""
    if isinstance(value, float):
        if math.isnan(value):
            raise ValidationError(f"{name} is NaN")
        if math.isinf(value):
            raise ValidationError(f"{name} is Inf")
    return value


def validate_price(value: float, name: str = "price", min_val: float = 0.0, max_val: float = 1_000_000.0) -> float:
    """Validate a price: no NaN/Inf, within reasonable bounds."""
    validate_no_nan_inf(value, name)
    if value < min_val:
        raise ValidationError(f"{name} {value} < minimum {min_val}")
    if value > max_val:
        raise ValidationError(f"{name} {value} > maximum {max_val}")
    return value


def validate_quantity(value: float, name: str = "quantity") -> float:
    """Validate quantity: positive, finite."""
    validate_no_nan_inf(value, name)
    if value <= 0:
        raise ValidationError(f"{name} must be > 0, got {value}")
    return value


def validate_dataframe(df: pd.DataFrame, required_cols: Optional[list] = None, allow_nan: bool = False) -> pd.DataFrame:
    """
    Validate a market data DataFrame.
    - Required columns must exist
    - NaN/Inf in numeric columns are rejected unless allow_nan=True
    """
    if df.empty:
        raise ValidationError("DataFrame is empty")

    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

    if not allow_nan:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                raise ValidationError(f"Column '{col}' contains NaN values")
            if np.isinf(df[col]).any():
                raise ValidationError(f"Column '{col}' contains Inf values")

    return df


def validate_event_dict(event: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a generic event dict for serialization safety."""
    def _check(obj, path: str = ""):
        if isinstance(obj, float):
            if math.isnan(obj):
                raise ValidationError(f"NaN found at {path}")
            if math.isinf(obj):
                raise ValidationError(f"Inf found at {path}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check(v, f"{path}[{i}]")

    _check(event)
    return event

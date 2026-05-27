"""
MLOps package for AnatoliaX Auto-Trader: model registry, drift detection, and monitoring.

Provides ML model lifecycle management, versioning, and production monitoring
capabilities for algorithmic trading strategies.
"""

from mlops.model_registry import ModelRegistry
from mlops.drift_detector import DriftDetector

__all__ = [
    'ModelRegistry',
    'DriftDetector',
]

__version__ = '1.0.0'

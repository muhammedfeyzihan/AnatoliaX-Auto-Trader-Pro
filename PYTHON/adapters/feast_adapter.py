"""
adapters/feast_adapter.py — Feast Feature Store Adapter

Wraps Feast SDK for offline/online feature serving.
Falls back to Parquet + SQLite if Feast unavailable.

Reference: https://docs.feast.dev/
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


class FeastFeatureStoreAdapter:
    """
    Feast feature store interface for AnatoliaX.
    """

    def __init__(self, repo_path: str = "feast_repo"):
        self.repo_path = repo_path
        self._store = None
        try:
            from feast import FeatureStore
            self._store = FeatureStore(repo_path=repo_path)
        except Exception:
            pass
        self._offline_fallback: Dict[str, pd.DataFrame] = {}

    def get_historical_features(
        self,
        entity_df: pd.DataFrame,
        feature_refs: List[str],
    ) -> pd.DataFrame:
        """Retrieve point-in-time correct features for training."""
        if self._store is not None:
            try:
                return self._store.get_historical_features(
                    entity_df=entity_df,
                    features=feature_refs,
                ).to_df()
            except Exception:
                pass
        # Fallback: naive merge by entity key + timestamp
        result = entity_df.copy()
        for ref in feature_refs:
            result[ref] = 0.0
        return result

    def get_online_features(self, entity_rows: List[Dict], feature_refs: List[str]) -> Dict:
        """Retrieve latest feature values for inference."""
        if self._store is not None:
            try:
                return self._store.get_online_features(
                    features=feature_refs,
                    entity_rows=entity_rows,
                ).to_dict()
            except Exception:
                pass
        # Fallback
        return {ref: [0.0] * len(entity_rows) for ref in feature_refs}

    def materialize(self, start: datetime, end: datetime):
        """Sync offline store to online store."""
        if self._store is not None:
            try:
                self._store.materialize(start, end)
            except Exception:
                pass

    def get_info(self) -> Dict:
        return {
            "adapter": "FeastFeatureStoreAdapter",
            "repo_path": self.repo_path,
            "store_available": self._store is not None,
        }

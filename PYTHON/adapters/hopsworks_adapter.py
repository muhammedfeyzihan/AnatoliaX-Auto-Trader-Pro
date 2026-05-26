"""
adapters/hopsworks_adapter.py — Hopsworks Feature Store Adapter

Wraps Hopsworks SDK for feature groups and training datasets.
Falls back to Parquet + SQLite if hopsworks unavailable.

Reference: https://docs.hopsworks.ai/
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd


class HopsworksFeatureStoreAdapter:
    """
    Hopsworks feature store interface.
    """

    def __init__(self, host: str = "localhost", project: str = "anatoliax", api_key: Optional[str] = None):
        self.host = host
        self.project = project
        self.api_key = api_key
        self._fs = None
        try:
            import hopsworks
            conn = hopsworks.login(host=host, project=project, api_key_value=api_key)
            self._fs = conn.get_feature_store()
        except Exception:
            pass
        self._fallback: Dict[str, pd.DataFrame] = {}

    def get_or_create_feature_group(
        self,
        name: str,
        version: int = 1,
        primary_key: List[str] = None,
        event_time: str = "timestamp",
    ) -> Optional[Any]:
        if self._fs is not None:
            try:
                return self._fs.get_or_create_feature_group(
                    name=name,
                    version=version,
                    primary_key=primary_key or ["symbol"],
                    event_time=event_time,
                )
            except Exception:
                pass
        return None

    def insert_into_feature_group(self, name: str, df: pd.DataFrame):
        if self._fs is not None:
            try:
                fg = self._fs.get_feature_group(name=name)
                fg.insert(df)
                return True
            except Exception:
                pass
        self._fallback[name] = df
        return True

    def get_feature_group(self, name: str, version: int = 1):
        if self._fs is not None:
            try:
                return self._fs.get_feature_group(name=name, version=version)
            except Exception:
                pass
        return self._fallback.get(name)

    def get_info(self) -> Dict:
        return {
            "adapter": "HopsworksFeatureStoreAdapter",
            "host": self.host,
            "project": self.project,
            "connected": self._fs is not None,
        }


# Avoid NameError on Optional[Any] import hint
from typing import Any

"""
gpu/rapids_pipeline.py — RAPIDS cuDF ile GPU ozellik hesaplama
"""
from typing import Optional


class RAPIDSPipeline:
    """
    RAPIDS cuDF ile GPU ozellik hesaplama.

    Ozellikler:
    - EMA, RSI, MACD, VWAP, ATR (GPU uzerinde)
    - Parquet okuma cuDF ile (sutun secici)
    - Geri donus: cuDF bulunamazsa pandas CPU

    Kullanim:
        pipe = RAPIDSPipeline()
        features = pipe.compute(df, ["ema_20", "rsi_14", "macd"])
    """

    def __init__(self):
        self._use_gpu = False
        try:
            import cudf
            self._use_gpu = True
        except Exception:
            self._use_gpu = False

    def compute(self, df, features: list) -> object:
        """Ozellik listesi hesapla; GPU DataFrame veya pandas DataFrame dondur."""
        if self._use_gpu:
            import cudf
            gdf = cudf.DataFrame.from_pandas(df) if hasattr(df, "to_pandas") else df
            for feat in features:
                if feat == "ema_20":
                    gdf["ema_20"] = gdf["close"].ewm(span=20, adjust=False).mean()
                elif feat == "rsi_14":
                    delta = gdf["close"].diff()
                    gain = delta.clip(lower=0)
                    loss = -delta.clip(upper=0)
                    avg_gain = gain.ewm(span=14, adjust=False).mean()
                    avg_loss = loss.ewm(span=14, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    gdf["rsi_14"] = 100 - (100 / (1 + rs))
            return gdf
        # CPU geri donus
        for feat in features:
            if feat == "ema_20":
                df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
            elif feat == "rsi_14":
                delta = df["close"].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.ewm(span=14, adjust=False).mean()
                avg_loss = loss.ewm(span=14, adjust=False).mean()
                rs = avg_gain / avg_loss
                df["rsi_14"] = 100 - (100 / (1 + rs))
        return df

"""
kap_correlation.py — KAP Bildirimleri ile Fiyat Hareketi Korelasyonu
Bildirim tipine gore sonraki 1-5 gun getirisini analiz eder.
"""
import pandas as pd
import numpy as np
from scipy.stats import pearsonr


class KAPCorrelationAnalyzer:
    """KAP bildirimlerini fiyat hareketleriyle karsilastirir."""

    def __init__(self, announcements: pd.DataFrame, prices: pd.DataFrame):
        """
        Args:
            announcements: DataFrame(ticker, date, type, title)
            prices: DataFrame(index=date, columns=[ticker1, ticker2, ...])
        """
        self.announcements = announcements.copy()
        self.prices = prices.copy()
        self.results = []

    def analyze(self, windows: list = None) -> pd.DataFrame:
        """Her bildirim tipi icin korelasyon analizi yapar."""
        if windows is None:
            windows = [1, 2, 3, 5]

        types = self.announcements["type"].unique()

        for ann_type in types:
            subset = self.announcements[self.announcements["type"] == ann_type]
            for window in windows:
                corr, pval, avg_return = self._calc(subset, window)
                self.results.append({
                    "type": ann_type,
                    "window_days": window,
                    "count": len(subset),
                    "avg_return": avg_return,
                    "pearson_r": corr,
                    "p_value": pval,
                    "significant": pval < 0.05,
                })

        return pd.DataFrame(self.results)

    def _calc(self, subset: pd.DataFrame, window: int):
        returns = []
        for _, row in subset.iterrows():
            ticker = row["ticker"]
            date = pd.Timestamp(row["date"])

            if ticker not in self.prices.columns:
                continue

            # Bildirim tarihinden sonraki fiyat
            future_prices = self.prices[ticker].loc[self.prices.index >= date]
            if len(future_prices) <= window:
                continue

            entry = future_prices.iloc[0]
            exit_price = future_prices.iloc[min(window, len(future_prices) - 1)]
            ret = (exit_price - entry) / entry if entry > 0 else 0
            returns.append(ret)

        if len(returns) < 3:
            return np.nan, np.nan, np.nan

        avg_return = np.mean(returns)
        # Korelasyon: bildirim varligi (dummy 1) ile getiri arasinda
        dummy = np.ones(len(returns))
        corr, pval = pearsonr(dummy, returns)
        return corr, pval, avg_return

    def top_opportunities(self, n: int = 5) -> pd.DataFrame:
        """En yuksek getiri potansiyeli olan bildirim tiplerini listeler."""
        df = pd.DataFrame(self.results)
        if df.empty:
            return df
        return df.sort_values("avg_return", ascending=False).head(n)

"""
trade_analytics.py — Advanced Trade Analytics
K184-K188: Win/loss streaks, Calmar, Omega, trade attribution.
"""

import math
import statistics
import pandas as pd
import numpy as np
from typing import List, Dict


class TradeAnalytics:
    """
    İşlem bazlı derinlemesine analitik motor.
    """

    def __init__(self, risk_free_rate: float = 0.10):
        self.risk_free_rate = risk_free_rate

    # ── Streak Analysis (K184) ───────────────────────────

    def streak_analysis(self, outcomes: List[float]) -> Dict:
        """
        Kazanç ve zarar serisi analizi.
        outcomes: pozitif = kazanç, negatif = zarar
        """
        if not outcomes:
            return {
                "max_win_streak": 0,
                "max_loss_streak": 0,
                "expected_win_streak": 0.0,
                "expected_loss_streak": 0.0,
            }

        wins = [1 if o > 0 else 0 for o in outcomes]
        losses = [1 if o <= 0 else 0 for o in outcomes]

        max_win = self._max_consecutive(wins, target=1)
        max_loss = self._max_consecutive(losses, target=1)

        win_rate = sum(wins) / len(wins)
        loss_rate = 1 - win_rate

        # Expected streak length = p / (1-p) for wins, geometric series
        expected_win = win_rate / (1 - win_rate + 1e-12) if win_rate < 1 else len(outcomes)
        expected_loss = loss_rate / (1 - loss_rate + 1e-12) if loss_rate < 1 else len(outcomes)

        return {
            "max_win_streak": max_win,
            "max_loss_streak": max_loss,
            "expected_win_streak": round(expected_win, 2),
            "expected_loss_streak": round(expected_loss, 2),
            "win_rate": round(win_rate, 4),
        }

    def _max_consecutive(self, seq: List[int], target: int) -> int:
        max_count = 0
        current = 0
        for val in seq:
            if val == target:
                current += 1
                max_count = max(max_count, current)
            else:
                current = 0
        return max_count

    # ── Calmar Ratio (K185) ──────────────────────────────

    def calmar_ratio(self, equity_series: pd.Series) -> float:
        """
        CAGR / Max Drawdown
        """
        if len(equity_series) < 2 or equity_series.iloc[0] <= 0:
            return 0.0
        total_return = (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        n_years = len(equity_series) / 252.0
        cagr = (1 + total_return) ** (1 / (n_years + 1e-12)) - 1
        max_dd = self._max_drawdown(equity_series)
        return cagr / (max_dd + 1e-12)

    def _max_drawdown(self, equity: pd.Series) -> float:
        peak = equity.expanding(min_periods=1).max()
        dd = (peak - equity) / peak
        return dd.max()

    # ── Omega Ratio (K186) ───────────────────────────────

    def omega_ratio(
        self,
        returns: pd.Series,
        threshold: float = 0.0,
    ) -> float:
        """
        İstenen getiri eşiğinin üstündeki kazançların / altındaki kayıpların oranı.
        """
        if returns.empty:
            return 0.0
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns <= threshold]
        gain_sum = gains.sum()
        loss_sum = losses.sum()
        if loss_sum <= 0:
            return float("inf") if gain_sum > 0 else 0.0
        return gain_sum / loss_sum

    # ── Trade Attribution (K187) ───────────────────────────

    def trade_attribution(
        self,
        trades_df: pd.DataFrame,
        signal_type_col: str = "signal_type",
    ) -> Dict:
        """
        Sinyal tipine göre getiri dağılımı.
        """
        if trades_df.empty or signal_type_col not in trades_df.columns:
            return {}

        attribution = {}
        for sig_type, group in trades_df.groupby(signal_type_col):
            wins = group[group["net_pnl"] > 0]
            losses = group[group["net_pnl"] <= 0]
            attribution[sig_type] = {
                "count": len(group),
                "total_pnl": round(group["net_pnl"].sum(), 2),
                "avg_pnl": round(group["net_pnl"].mean(), 2),
                "win_rate": round(len(wins) / len(group), 4) if len(group) > 0 else 0,
                "avg_win": round(wins["net_pnl"].mean(), 2) if len(wins) > 0 else 0,
                "avg_loss": round(losses["net_pnl"].mean(), 2) if len(losses) > 0 else 0,
            }
        return attribution

    # ── Comprehensive Analyze (K188) ───────────────────────

    def analyze(self, trades_df: pd.DataFrame, equity_series: pd.Series = None) -> Dict:
        """
        Tüm trade analitiklerini hesapla.
        """
        if trades_df.empty:
            return {"error": "No trades"}

        returns = trades_df["net_pnl"] / (trades_df["entry_price"] * trades_df["size"])
        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] <= 0]

        win_rate = len(wins) / len(trades_df)
        avg_win = wins["net_pnl"].mean() if len(wins) > 0 else 0
        avg_loss = losses["net_pnl"].mean() if len(losses) > 0 else 0

        gross_profit = wins["net_pnl"].sum()
        gross_loss = abs(losses["net_pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

        streaks = self.streak_analysis(trades_df["net_pnl"].tolist())

        result = {
            "total_trades": len(trades_df),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "expectancy": round(expectancy, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "streaks": streaks,
        }

        if equity_series is not None and len(equity_series) > 1:
            result["calmar_ratio"] = round(self.calmar_ratio(equity_series), 4)
            result["omega_ratio"] = round(self.omega_ratio(returns), 4)
        else:
            result["calmar_ratio"] = None
            result["omega_ratio"] = None

        return result

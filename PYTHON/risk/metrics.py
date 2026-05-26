"""
metrics.py — K114-K121 Performans Metriklerinin Python Implementasyonu
Sharpe > 1.5, Sortino > 1.5, Max Drawdown < %10, Profit Factor > 1.5, Recovery Factor > 3
"""
import pandas as pd
import numpy as np
from backtest import performance as perf


def calculate_portfolio_metrics(trades_df: pd.DataFrame, capital_history: pd.Series) -> dict:
    """Portfoy metriklerini hesaplar."""
    if trades_df.empty:
        return {"error": "Yeterli islem yok"}

    # Temel istatistikler
    returns = trades_df["net_pnl"] / (trades_df["entry_price"] * trades_df["size"])
    wins = trades_df[trades_df["net_pnl"] > 0]
    losses = trades_df[trades_df["net_pnl"] <= 0]

    win_rate = len(wins) / len(trades_df)
    avg_win = wins["net_pnl"].mean() if len(wins) > 0 else 0
    avg_loss = losses["net_pnl"].mean() if len(losses) > 0 else 0
    gross_profit = wins["net_pnl"].sum()
    gross_loss = abs(losses["net_pnl"].sum())

    # Equity curve
    equity = capital_history if capital_history is not None else trades_df["net_pnl"].cumsum() + 100_000

    # Metrikler
    sharpe = perf.sharpe_ratio(returns)
    sortino = perf.sortino_ratio(returns)
    max_dd = perf.max_drawdown(equity)
    pf = perf.profit_factor(gross_profit, gross_loss)
    exp = perf.expectancy(win_rate, avg_win, avg_loss)
    rec = perf.recovery_factor(equity.iloc[-1] - equity.iloc[0], max_dd) if len(equity) > 1 else 0
    mc = perf.monte_carlo(returns)
    wf = perf.walk_forward_analysis(returns)

    # Esik kontrolu
    thresholds = {
        "sharpe": (sharpe, 1.5, ">"),
        "sortino": (sortino, 1.5, ">"),
        "max_drawdown": (max_dd, 0.10, "<"),
        "profit_factor": (pf, 1.5, ">"),
        "recovery_factor": (rec, 3.0, ">"),
        "expectancy": (exp, 0, ">"),
    }

    status = {}
    passed = 0
    for name, (value, threshold, op) in thresholds.items():
        ok = (value > threshold) if op == ">" else (value < threshold)
        status[name] = {"value": value, "threshold": threshold, "passed": ok}
        if ok:
            passed += 1

    status["monte_carlo"] = mc
    status["walk_forward"] = wf
    status["_summary"] = f"{passed}/7 temel metrik basarili"
    status["_overall"] = "ONAY" if passed >= 5 else "RED"

    return status

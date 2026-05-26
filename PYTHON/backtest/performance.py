"""
performance.py — Gelişmiş Performans Metrikleri (K114-K121)
Sharpe, Sortino, Max Drawdown, Expectancy, Profit Factor, Monte Carlo, Walk-Forward
"""
import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Sharpe Ratio = (Ort Getiri - Risksiz) / Std Sapma. Esik: > 1.0"""
    excess = returns - risk_free
    std = returns.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return excess.mean() / std


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Sortino Ratio = (Ort Getiri - Risksiz) / Downside Sapma. Esik: > 1.5"""
    excess = returns.mean() - risk_free
    downside = returns[returns < 0].std()
    if downside == 0 or np.isnan(downside):
        return 0.0
    return excess / downside


def max_drawdown(equity: pd.Series) -> float:
    """Max Drawdown = (Zirve - Dibe) / Zirve. Esik: < %20"""
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    return abs(drawdown.min())


def expectancy(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss). Esik: > 0"""
    loss_rate = 1 - win_rate
    return (win_rate * avg_win) - (loss_rate * abs(avg_loss))


def profit_factor(gross_profit: float, gross_loss: float) -> float:
    """Profit Factor = Toplam Kar / Toplam Zarar. Esik: > 1.5"""
    if gross_loss == 0:
        return np.inf if gross_profit > 0 else 0.0
    return gross_profit / abs(gross_loss)


def recovery_factor(net_profit: float, max_dd: float) -> float:
    """Recovery Factor = Net Profit / Max Drawdown. Esik: > 3"""
    if max_dd == 0:
        return 0.0
    return net_profit / max_dd


def monte_carlo(returns: pd.Series, simulations: int = 10000, confidence: float = 0.95) -> dict:
    """Monte Carlo simulasyonu — vektorize (100x+ hizli)."""
    np.random.seed(42)
    arr = np.asarray(returns)
    n = len(arr)
    # Vektorize: (simulations, n) matrisi tek hamlede
    samples = np.random.choice(arr, size=(simulations, n), replace=True)
    sim_results = samples.sum(axis=1)

    lower = np.percentile(sim_results, (1 - confidence) / 2 * 100)
    upper = np.percentile(sim_results, (1 + confidence) / 2 * 100)
    loss_prob = (sim_results < 0).mean()

    return {
        "ci_lower": float(lower),
        "ci_upper": float(upper),
        "loss_probability": float(loss_prob),
        "mean": float(sim_results.mean()),
        "median": float(np.median(sim_results)),
        "min": float(sim_results.min()),
        "max": float(sim_results.max()),
    }


def walk_forward_analysis(returns: pd.Series, train_ratio: float = 0.7, threshold: float = 0.10) -> dict:
    """Walk-forward: In-Sample vs Out-of-Sample. Esik: fark < %10."""
    split = int(len(returns) * train_ratio)
    in_sample = returns[:split]
    out_sample = returns[split:]

    in_sharpe = sharpe_ratio(in_sample)
    out_sharpe = sharpe_ratio(out_sample)
    diff = abs(in_sharpe - out_sharpe)

    return {
        "in_sample_sharpe": in_sharpe,
        "out_sample_sharpe": out_sharpe,
        "difference": diff,
        "overfitting": diff > threshold,
    }


def calculate_all_metrics(trades: pd.DataFrame, equity: pd.Series, risk_free: float = 0.0) -> dict:
    """Tum metrikleri hesaplar ve dashboard formatinda dondurur."""
    if trades is None or trades.empty:
        # Bos trades: varsayim metrikleri dondur
        return {
            "Sharpe Ratio": {"value": 0.0, "min": 1.0, "status": "❌"},
            "Sortino Ratio": {"value": 0.0, "min": 1.5, "status": "❌"},
            "Max Drawdown": {"value": "0%", "min": "<%20", "status": "✅"},
            "Win Rate": {"value": "0%", "min": ">%55", "status": "❌"},
            "Profit Factor": {"value": 0.0, "min": 1.5, "status": "❌"},
            "Expectancy": {"value": 0.0, "min": ">0", "status": "❌"},
            "Monte Carlo %95": {"value": "[0, 0]", "min": "Pozitif", "status": "❌"},
            "Walk-Forward Fark": {"value": "0%", "min": "<%10", "status": "✅"},
            "_summary": "0/8 metrik basarili — RED",
        }

    returns = trades["comm_net_return"] if "comm_net_return" in trades.columns else (trades["exit_price"] - trades["entry_price"]) / trades["entry_price"]

    wins = trades[trades["comm_net_profit"] > 0] if "comm_net_profit" in trades.columns else trades[returns > 0]
    losses = trades[trades["comm_net_profit"] <= 0] if "comm_net_profit" in trades.columns else trades[returns <= 0]

    win_rate = len(wins) / len(trades) if len(trades) > 0 else 0
    avg_win = wins["comm_net_return"].mean() if "comm_net_return" in wins.columns and len(wins) > 0 else 0
    avg_loss = losses["comm_net_return"].mean() if "comm_net_return" in losses.columns and len(losses) > 0 else 0

    gross_profit = wins["comm_net_profit"].sum() if "comm_net_profit" in wins.columns else 0
    gross_loss = losses["comm_net_profit"].sum() if "comm_net_profit" in losses.columns else 0

    metrics = {
        "sharpe": sharpe_ratio(returns, risk_free),
        "sortino": sortino_ratio(returns, risk_free),
        "max_drawdown": max_drawdown(equity),
        "win_rate": win_rate,
        "profit_factor": profit_factor(gross_profit, gross_loss),
        "expectancy": expectancy(win_rate, avg_win, avg_loss),
        "recovery_factor": recovery_factor(equity.iloc[-1] - equity.iloc[0], max_drawdown(equity)) if len(equity) > 0 else 0,
        "monte_carlo": monte_carlo(returns),
        "walk_forward": walk_forward_analysis(returns),
    }

    # Dashboard formati (K121)
    dashboard = {
        "Sharpe Ratio": {"value": round(metrics["sharpe"], 2), "min": 1.0, "status": "✅" if metrics["sharpe"] > 1.0 else "❌"},
        "Sortino Ratio": {"value": round(metrics["sortino"], 2), "min": 1.5, "status": "✅" if metrics["sortino"] > 1.5 else "❌"},
        "Max Drawdown": {"value": f"%{metrics['max_drawdown']*100:.1f}", "min": "<%20", "status": "✅" if metrics["max_drawdown"] < 0.20 else "❌"},
        "Win Rate": {"value": f"%{metrics['win_rate']*100:.1f}", "min": ">%55", "status": "✅" if metrics["win_rate"] > 0.55 else "❌"},
        "Profit Factor": {"value": round(metrics["profit_factor"], 2), "min": 1.5, "status": "✅" if metrics["profit_factor"] > 1.5 else "❌"},
        "Expectancy": {"value": round(metrics["expectancy"], 4), "min": ">0", "status": "✅" if metrics["expectancy"] > 0 else "❌"},
        "Monte Carlo %95": {"value": f"[{metrics['monte_carlo']['ci_lower']:.2f}, {metrics['monte_carlo']['ci_upper']:.2f}]", "min": "Pozitif", "status": "✅" if metrics["monte_carlo"]["ci_lower"] > 0 else "❌"},
        "Walk-Forward Fark": {"value": f"%{metrics['walk_forward']['difference']*100:.1f}", "min": "<%10", "status": "✅" if not metrics["walk_forward"]["overfitting"] else "❌"},
    }

    passed = sum(1 for v in dashboard.values() if v["status"] == "✅")
    dashboard["_summary"] = f"{passed}/8 metrik basarili — {'ONAY' if passed >= 6 else 'RED'}"
    return dashboard

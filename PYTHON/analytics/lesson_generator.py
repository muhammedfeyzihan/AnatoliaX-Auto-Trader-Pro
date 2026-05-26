"""
lesson_generator.py — Backtest sonuclarindan derinlemesine ders cikarma.
AutoTrader'dan esinlenilmis: "Why did this trade lose? What can we learn?"

Kullanim:
    from analytics.lesson_generator import LessonGenerator
    lg = LessonGenerator()
    lessons = lg.analyze_backtest(trades_df, metrics_dict)
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import json
import pandas as pd
from datetime import datetime
from typing import Optional


class LessonGenerator:
    """
    Her backtest sonrasinda sistematik ders cikarir.
    - Hangi senaryolarda yanlis tahmin?
    - SL mi erken, TP mi gec vuruldu?
    - Volatilite arttiginda ne oldu?
    - Komisyon ne kadar etkiledi?
    """

    def __init__(self, output_dir: str | Path = "memory/lessons"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_backtest(
        self,
        trades_df: pd.DataFrame,
        metrics: dict,
        symbol: str = "UNKNOWN",
        strategy: str = "UNKNOWN",
    ) -> dict:
        """
        Backtest sonuclarini analiz et ve dersler uret.
        Returns: {"symbol": str, "strategy": str, "timestamp": str, "lessons": list, "action_items": list}
        """
        lessons: list[dict] = []
        action_items: list[str] = []

        if trades_df.empty:
            return {
                "symbol": symbol,
                "strategy": strategy,
                "timestamp": datetime.now().isoformat(),
                "lessons": [{"pattern": "No trades", "suggestion": "Sinyal uretilemedi, veri veya esik kontrol edilmeli"}],
                "action_items": ["Sinyal esigi dusurulup tekrar denenmeli"],
            }

        df = trades_df.copy()
        total = len(df)
        wins = df[df["net_pnl"] > 0]
        losses = df[df["net_pnl"] < 0]

        # 1. Win/Loss orani ve kalitesi
        win_rate = len(wins) / total if total > 0 else 0.0
        avg_win = wins["net_pnl"].mean() if not wins.empty else 0.0
        avg_loss = losses["net_pnl"].mean() if not losses.empty else 0.0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        lessons.append({
            "pattern": "Win/Loss kalitesi",
            "win_rate": round(win_rate * 100, 1),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "suggestion": (
                "Profit factor guclu, trend takip artirilabilir." if profit_factor > 2.0
                else "Profit factor dusuk, SL daraltilmali veya R:R artirilmali." if profit_factor < 1.5
                else "Kabul edilebilir profit factor, optimizasyona acik."
            ),
        })

        # 2. SL erken mi tetiklendi?
        sl_trades = df[df["reason"].isin(["SL", "TRAILING_STOP"])]
        if not sl_trades.empty:
            avg_sl_bars = (sl_trades["exit_idx"] - sl_trades["entry_idx"]).mean()
            if avg_sl_bars < 8:
                lessons.append({
                    "pattern": "Erken SL",
                    "avg_bars_to_sl": round(float(avg_sl_bars), 1),
                    "count": int(len(sl_trades)),
                    "suggestion": f"SL ortalama {avg_sl_bars:.0f} bar sonra tetiklendi. SL mesafesi artirilmali.",
                })
                action_items.append(f"{symbol} icin SL mesafesini artir ({avg_sl_bars:.0f} bar ortalama)")
            else:
                lessons.append({
                    "pattern": "SL zamani",
                    "avg_bars_to_sl": round(float(avg_sl_bars), 1),
                    "suggestion": "SL zamani makul, erken degil.",
                })

        # 3. TP isabet orani ve vurulma zamani
        tp_trades = df[df["reason"].str.startswith("TP", na=False)]
        if not tp_trades.empty:
            avg_tp_bars = (tp_trades["exit_idx"] - tp_trades["entry_idx"]).mean()
            lessons.append({
                "pattern": "TP isabet",
                "count": int(len(tp_trades)),
                "avg_bars_to_tp": round(float(avg_tp_bars), 1),
                "suggestion": (
                    "TP cok gec vuruluyor, momentum filtresi eklenmeli." if avg_tp_bars > 30
                    else "TP zamani kabul edilebilir."
                ),
            })

        # 4. Time exit analizi
        time_exits = df[df["reason"] == "TIME_EXIT"]
        if len(time_exits) > 2:
            time_pnl = time_exits["net_pnl"].mean()
            lessons.append({
                "pattern": "Time exit performansi",
                "count": int(len(time_exits)),
                "avg_pnl": round(float(time_pnl), 2),
                "suggestion": (
                    "Time exit zararli, max bar artirilmali veya trend filtresi eklenmeli." if time_pnl < 0
                    else "Time exit kabul edilebilir."
                ),
            })
            if time_pnl < 0:
                action_items.append(f"{symbol} time exit limitini artir (zararli kapanis)")

        # 5. Komisyon etkisi
        total_comm = df["commission"].sum()
        gross_pnl = df["gross_pnl"].sum()
        if gross_pnl != 0:
            comm_impact = abs(total_comm / gross_pnl) * 100
            lessons.append({
                "pattern": "Komisyon etkisi",
                "comm_vs_gross_pct": round(float(comm_impact), 1),
                "suggestion": (
                    f"Komisyon gross PnL'nin %{comm_impact:.0f}'si. Islem sikligi dusurulmeli." if comm_impact > 20
                    else f"Komisyon etkisi makul (%{comm_impact:.0f})."
                ),
            })

        # 6. Drawdown pattern
        max_dd = metrics.get("max_drawdown", 0.0)
        if max_dd < -10.0:
            lessons.append({
                "pattern": "Derin drawdown",
                "max_drawdown": round(float(max_dd), 1),
                "suggestion": "Max drawdown %10'un uzerinde. Gunluk kayip limiti veya pozisyon kucultme sarti.",
            })
            action_items.append(f"{symbol} gunluk kayip limitini daralt (drawdown {max_dd:.1f}%)")

        # 7. Sharpe / Sortino
        sharpe = metrics.get("sharpe_ratio", 0.0)
        if sharpe < 1.0:
            lessons.append({
                "pattern": "Dusuk risk-ayarli getiri",
                "sharpe": round(float(sharpe), 2),
                "suggestion": "Sharpe ratio dusuk. Risk azaltilmali veya daha yuksek olasilikli setuplar secilmeli.",
            })

        result = {
            "symbol": symbol,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_trades": total,
                "win_count": int(len(wins)),
                "loss_count": int(len(losses)),
                "win_rate": round(win_rate * 100, 1),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(float(metrics.get("max_drawdown", 0)), 1),
            },
            "lessons": lessons,
            "action_items": action_items,
        }

        # Kaydet
        self._save(result)
        return result

    def _save(self, result: dict):
        fname = f"{result['symbol']}_{result['strategy']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.output_dir / fname
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def get_latest_lesson(self, symbol: str) -> Optional[dict]:
        """Son kaydedilen dersi getir."""
        files = sorted(self.output_dir.glob(f"{symbol}_*.json"), reverse=True)
        if files:
            return json.loads(files[0].read_text(encoding="utf-8"))
        return None

    def get_all_action_items(self) -> list[str]:
        """Tum derslerden action item'lari birlestir."""
        items = []
        for f in self.output_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            items.extend(data.get("action_items", []))
        return items


if __name__ == "__main__":
    import numpy as np
    trades = pd.DataFrame({
        "entry_idx": [0, 10, 20, 30],
        "exit_idx": [5, 18, 40, 50],
        "entry_price": [100.0, 102.0, 101.0, 103.0],
        "exit_price": [101.0, 100.0, 105.0, 102.0],
        "net_pnl": [50.0, -80.0, 120.0, -30.0],
        "gross_pnl": [55.0, -75.0, 125.0, -25.0],
        "commission": [5.0, 5.0, 5.0, 5.0],
        "reason": ["TP1", "SL", "TP2", "SL"],
    })
    metrics = {"sharpe_ratio": 0.8, "max_drawdown": -12.5}
    lg = LessonGenerator()
    result = lg.analyze_backtest(trades, metrics, symbol="THYAO", strategy="SIGNAL_ENGINE")
    print(json.dumps(result, ensure_ascii=False, indent=2))

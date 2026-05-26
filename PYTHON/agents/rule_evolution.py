"""
rule_evolution.py — Kural Evrim Motoru
Ajan performans verilerini analiz eder, ayi/volatilite kosullarina gore
kurallari otomatik olarak ayarlar. "AGI hizi" ile kendini gelistirir.

Kullanim:
    from agents.rule_evolution import RuleEvolution
    evo = RuleEvolution()
    suggestions = evo.analyze_and_evolve()
    # suggestions: [{"rule": "SL", "old": "2%", "new": "1.5%", "reason": "..."}]
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "performance.db"
EVOLUTION_LOG_PATH = Path(__file__).resolve().parents[2] / "memory" / "rule_evolution.json"


class RuleEvolution:
    """
    Performans verilerine dayali kural evrimi:
    - Ayi piyasasi: Daha dar SL, dusuk Kelly, az pozisyon
    - Yuksek volatilite: ATR bazli genislet/daralt
    - Dusuk win rate: Sinyal esigini yukselt
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.evolution_log = EVOLUTION_LOG_PATH
        self.evolution_log.parent.mkdir(parents=True, exist_ok=True)

    def _load_trades(self, days: int = 30) -> list[dict]:
        """Son N gunluk islemleri yukle."""
        if not self.db_path.exists():
            return []
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT symbol, entry_price, exit_price, pnl_pct, outcome, timestamp, regime FROM trade_outcomes WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,),
            )
            rows = cursor.fetchall()
        return [
            {
                "symbol": r[0],
                "entry": r[1],
                "exit": r[2],
                "pnl_pct": r[3],
                "outcome": r[4],
                "timestamp": r[5],
                "regime": r[6] or "UNKNOWN",
            }
            for r in rows
        ]

    def _calculate_win_rate(self, trades: list[dict]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        return wins / len(trades)

    def _calculate_avg_metrics(self, trades: list[dict]) -> dict:
        if not trades:
            return {"avg_pnl": 0.0, "max_dd": 0.0, "avg_sl_distance": 0.0}
        pnls = [t["pnl_pct"] for t in trades]
        avg_pnl = sum(pnls) / len(pnls)
        cumulative = []
        running = 0
        for p in pnls:
            running += p
            cumulative.append(running)
        peak = max(cumulative) if cumulative else 0
        max_dd = min((c - peak) for c in cumulative) if cumulative else 0
        return {
            "avg_pnl": avg_pnl,
            "max_dd": max_dd,
            "trade_count": len(trades),
        }

    def analyze_and_evolve(self) -> list[dict]:
        """
        Performans analizi yap ve kural degisiklikleri oner.

        Donus: [{"rule": str, "old_value": any, "new_value": any, "reason": str, "confidence": float}]
        """
        trades = self._load_trades(days=30)
        if len(trades) < 10:
            return [{"rule": "NOP", "reason": "Yetersi islem sayisi (<10), evrim bekleniyor", "confidence": 0.0}]

        suggestions = []
        metrics = self._calculate_avg_metrics(trades)
        win_rate = self._calculate_win_rate(trades)

        # Ayi piyasasi tespiti
        bear_trades = [t for t in trades if t.get("regime") == "BEAR"]
        bull_trades = [t for t in trades if t.get("regime") == "BULL"]

        if bear_trades:
            bear_win = self._calculate_win_rate(bear_trades)
            if bear_win < 0.4:
                suggestions.append({
                    "rule": "SL_ATR_MULTIPLIER",
                    "old_value": 2.0,
                    "new_value": 1.5,
                    "reason": f"Ayi piyasasinda win rate dusuk ({bear_win:.0%}). SL daraltiliyor.",
                    "confidence": min(0.9, 0.5 + (0.4 - bear_win)),
                })
                suggestions.append({
                    "rule": "KELLY_CAP",
                    "old_value": 2.0,
                    "new_value": 1.0,
                    "reason": "Ayi piyasasinda pozisyon buyuklugu azaltiliyor.",
                    "confidence": 0.8,
                })
                suggestions.append({
                    "rule": "MAX_POSITIONS",
                    "old_value": 5,
                    "new_value": 3,
                    "reason": "Ayi piyasasinda max pozisyon sayisi dusuruluyor.",
                    "confidence": 0.7,
                })

        if bull_trades:
            bull_win = self._calculate_win_rate(bull_trades)
            if bull_win > 0.6:
                suggestions.append({
                    "rule": "SL_ATR_MULTIPLIER",
                    "old_value": 1.5,
                    "new_value": 2.0,
                    "reason": f"Boga piyasasinda win rate yuksek ({bull_win:.0%}). SL normale donuyor.",
                    "confidence": min(0.9, bull_win),
                })
                suggestions.append({
                    "rule": "KELLY_CAP",
                    "old_value": 1.0,
                    "new_value": 2.0,
                    "reason": "Boga piyasasinda Kelly normale donuyor.",
                    "confidence": 0.8,
                })

        # Genel win rate kontrolu
        if win_rate < 0.45:
            suggestions.append({
                "rule": "SIGNAL_THRESHOLD",
                "old_value": 70.0,
                "new_value": 80.0,
                "reason": f"Genel win rate dusuk ({win_rate:.0%}). Sinyal esigi yukseltiliyor.",
                "confidence": min(0.9, 0.5 + (0.45 - win_rate)),
            })
        elif win_rate > 0.65:
            suggestions.append({
                "rule": "SIGNAL_THRESHOLD",
                "old_value": 80.0,
                "new_value": 70.0,
                "reason": f"Genel win rate yuksek ({win_rate:.0%}). Sinyal esigi dusuruluyor.",
                "confidence": min(0.9, win_rate),
            })

        # Max drawdown kontrolu
        if metrics["max_dd"] < -5.0:
            suggestions.append({
                "rule": "DAILY_LOSS_LIMIT",
                "old_value": 3.0,
                "new_value": 2.0,
                "reason": f"Max drawdown yuksek ({metrics['max_dd']:.1f}%). Gunluk kayip limiti daraltiliyor.",
                "confidence": min(0.95, abs(metrics['max_dd']) / 10),
            })

        # Volatilite bazli SL ayari (ATR%
        high_vol_trades = [t for t in trades if abs(t["pnl_pct"]) > 5.0]
        if len(high_vol_trades) > len(trades) * 0.3:
            suggestions.append({
                "rule": "VOLATILITY_ADJUSTMENT",
                "old_value": False,
                "new_value": True,
                "reason": f"Yuksek volatilite islemleri fazla ({len(high_vol_trades)}/{len(trades)}). ATR bazli SL aktif.",
                "confidence": 0.85,
            })

        self._log_evolution(suggestions, metrics, win_rate)
        return suggestions

    def _log_evolution(self, suggestions: list[dict], metrics: dict, win_rate: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "win_rate": round(win_rate, 3),
            "suggestions": suggestions,
        }
        logs = []
        if self.evolution_log.exists():
            try:
                with open(self.evolution_log, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                pass
        logs.append(entry)
        with open(self.evolution_log, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def get_last_evolution(self) -> Optional[dict]:
        if not self.evolution_log.exists():
            return None
        with open(self.evolution_log, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-1] if logs else None

    def get_evolution_history(self) -> list[dict]:
        if not self.evolution_log.exists():
            return []
        with open(self.evolution_log, "r", encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    evo = RuleEvolution()
    suggestions = evo.analyze_and_evolve()
    print("Kural Evrim Onerileri:")
    for s in suggestions:
        print(f"  {s['rule']}: {s.get('old_value')} -> {s.get('new_value')} | {s['reason']} (guven: {s.get('confidence', 0):.0%})")

"""
performance_logger.py — Otomatik Performans Loglama
Her islem sonrasi sonuc takibi, ajan performans metrikleri, hata analizi.

Kullanim:
    from observability.performance_logger import PerformanceLogger
    logger = PerformanceLogger()
    logger.log_trade(trade_id=1, symbol="THYAO", expected_tp=320, actual_exit=310, pnl=1000, agent="Signal")
    logger.log_prediction(symbol="THYAO", agent="Signal", predicted_up=True, actual_up=True)
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
from pathlib import Path
from typing import Optional

LOG_DB = Path("data/performance_logs.db")
LOG_DB.parent.mkdir(parents=True, exist_ok=True)


class PerformanceLogger:
    """
    Islem sonuclarini ve ajan tahminlerini otomatik kaydeder.
    Gecmisteki kararlardan ders cikarilmasini saglar.
    """

    def __init__(self, db_path: Path = LOG_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        # Islem sonuc loglari
        c.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                symbol TEXT,
                entry_price REAL,
                exit_price REAL,
                expected_sl REAL,
                expected_tp1 REAL,
                expected_tp2 REAL,
                actual_pnl REAL,
                predicted_pnl REAL,
                agent TEXT,
                strategy TEXT,
                outcome TEXT,  -- WIN / LOSS / BREAKEVEN / PENDING
                created_at TEXT,
                notes TEXT
            )
        """)
        # Ajan tahmin loglari
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                agent TEXT,
                prediction TEXT,  -- UP / DOWN / NEUTRAL
                confidence REAL,
                actual_result TEXT,
                correct INTEGER,  -- 1 = dogru, 0 = yanlis
                prediction_date TEXT,
                result_date TEXT,
                market_regime TEXT
            )
        """)
        # Gunluk performans ozeti
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                date TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0.0,
                best_agent TEXT,
                worst_agent TEXT,
                avg_confidence REAL,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_trade(
        self,
        trade_id: int,
        symbol: str,
        entry_price: float,
        exit_price: Optional[float] = None,
        expected_sl: Optional[float] = None,
        expected_tp1: Optional[float] = None,
        expected_tp2: Optional[float] = None,
        actual_pnl: float = 0.0,
        predicted_pnl: Optional[float] = None,
        agent: str = "",
        strategy: str = "",
        notes: str = "",
    ):
        """Islem sonucunu kaydet."""
        outcome = "PENDING"
        if actual_pnl > 0:
            outcome = "WIN"
        elif actual_pnl < 0:
            outcome = "LOSS"
        elif actual_pnl == 0 and exit_price is not None:
            outcome = "BREAKEVEN"

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            INSERT INTO trade_outcomes
            (trade_id, symbol, entry_price, exit_price, expected_sl, expected_tp1, expected_tp2,
             actual_pnl, predicted_pnl, agent, strategy, outcome, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, symbol, entry_price, exit_price, expected_sl, expected_tp1, expected_tp2,
            actual_pnl, predicted_pnl, agent, strategy, outcome, datetime.now().isoformat(), notes,
        ))
        conn.commit()
        conn.close()

    def log_prediction(
        self,
        symbol: str,
        agent: str,
        prediction: str,  # UP / DOWN / NEUTRAL
        confidence: float = 0.0,
        market_regime: str = "NEUTRAL",
    ):
        """Ajan tahminini kaydet (sonuc henuz bilinmiyor)."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            INSERT INTO agent_predictions
            (symbol, agent, prediction, confidence, prediction_date, market_regime)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (symbol, agent, prediction, confidence, datetime.now().isoformat(), market_regime))
        conn.commit()
        conn.close()

    def update_prediction_result(
        self,
        symbol: str,
        agent: str,
        actual_result: str,  # UP / DOWN / NEUTRAL
    ):
        """Tahminin gerceklesen sonucunu guncelle."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        # Son tahmini bul
        c.execute("""
            SELECT id, prediction FROM agent_predictions
            WHERE symbol = ? AND agent = ? AND actual_result IS NULL
            ORDER BY prediction_date DESC LIMIT 1
        """, (symbol, agent))
        row = c.fetchone()
        if row:
            pred_id, prediction = row
            correct = 1 if prediction == actual_result else 0
            c.execute("""
                UPDATE agent_predictions
                SET actual_result = ?, correct = ?, result_date = ?
                WHERE id = ?
            """, (actual_result, correct, datetime.now().isoformat(), pred_id))
            conn.commit()
        conn.close()

    def get_agent_accuracy(self, agent: str, days: int = 30) -> dict:
        """Belirli bir ajanin dogruluk oranini hesapla."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute("""
            SELECT COUNT(*), SUM(correct) FROM agent_predictions
            WHERE agent = ? AND prediction_date > ?
        """, (agent, since))
        total, correct = c.fetchone()
        conn.close()

        if total is None or total == 0:
            return {"agent": agent, "total": 0, "correct": 0, "accuracy": 0.0}

        accuracy = (correct / total) * 100 if total > 0 else 0.0
        return {
            "agent": agent,
            "total": total,
            "correct": correct or 0,
            "accuracy": round(accuracy, 2),
        }

    def get_daily_summary(self, date_str: Optional[str] = None) -> dict:
        """Gunluk performans ozeti."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        # Islem sonuclari
        c.execute("""
            SELECT outcome, COUNT(*), SUM(actual_pnl) FROM trade_outcomes
            WHERE created_at LIKE ?
            GROUP BY outcome
        """, (f"{date_str}%",))
        rows = c.fetchall()
        conn.close()

        summary = {"date": date_str, "win": 0, "loss": 0, "breakeven": 0, "pending": 0, "total_pnl": 0.0}
        for outcome, count, pnl in rows:
            summary[outcome.lower()] = count
            if pnl:
                summary["total_pnl"] += pnl

        return summary

    def get_learning_insights(self, days: int = 30) -> list:
        """
        Gecmis hatalardan ders cikar: Hangi senaryolarda yanlis tahmin yapilmis?
        Returns: [{"pattern": str, "failure_rate": float, "suggestion": str}, ...]
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute("""
            SELECT market_regime, prediction, actual_result, COUNT(*)
            FROM agent_predictions
            WHERE prediction_date > ? AND actual_result IS NOT NULL
            GROUP BY market_regime, prediction, actual_result
        """, (since,))
        rows = c.fetchall()
        conn.close()

        insights = []
        # Basit analiz: Her rejimde hangi tahminler yanlis gitti
        regime_failures = {}
        for regime, pred, actual, count in rows:
            if pred != actual:
                key = f"{regime}_{pred}"
                regime_failures[key] = regime_failures.get(key, 0) + count

        for key, fail_count in regime_failures.items():
            parts = key.rsplit("_", 1)
            regime = parts[0]
            pred = parts[1]
            insights.append({
                "pattern": f"Rejim {regime} - Tahmin {pred}",
                "failure_count": fail_count,
                "suggestion": f"{regime} rejiminde {pred} tahmini dikkatli kullan",
            })

        return insights


if __name__ == "__main__":
    logger = PerformanceLogger()
    # Ornek loglama
    logger.log_trade(
        trade_id=1, symbol="THYAO", entry_price=300.0, exit_price=310.0,
        expected_tp1=320.0, actual_pnl=1000.0, agent="Sinyal", strategy="SIGNAL_ENGINE",
    )
    logger.log_prediction(symbol="THYAO", agent="Sinyal", prediction="UP", confidence=75.0, market_regime="BULL")
    logger.update_prediction_result(symbol="THYAO", agent="Sinyal", actual_result="UP")

    print("Ajan dogrulugu:", logger.get_agent_accuracy("Sinyal"))
    print("Gunluk ozet:", logger.get_daily_summary())
    print("Dersler:", logger.get_learning_insights())

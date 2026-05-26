"""
subscription_manager.py — Hisse basi alarm abonelik sistemi.
auto-marketplace'tan entegre edilmistir.

Kullanim:
    from telegram.subscription_manager import SubscriptionManager
    sm = SubscriptionManager()
    sm.add_subscription(user_id="YOUR_CHAT_ID_HERE", symbol="THYAO", condition={"type": "price_above", "value": 105.0})
    triggers = sm.check_subscriptions(symbol="THYAO", current_price=106.0)
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import sqlite3
import json
from datetime import datetime
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "subscriptions.db"


class SubscriptionManager:
    """
    Kullanici basi hisse alarm abonelikleri.
    Tetikleyiciler: fiyat threshold, RSI threshold, hacim patlamasi, sinyal skoru.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    condition_value REAL,
                    condition_extra TEXT,
                    created_at TEXT,
                    last_triggered TEXT,
                    active INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscription_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER,
                    triggered_at TEXT,
                    trigger_value REAL,
                    message TEXT
                )
                """
            )
            conn.commit()

    def add_subscription(
        self,
        user_id: str,
        symbol: str,
        condition: dict,
    ) -> int:
        """
        Yeni abonelik ekle.

        condition: {"type": "price_above"|"price_below"|"rsi_above"|"volume_spike"|"signal_score", "value": float}
        """
        sym = symbol.upper().strip()
        cond_type = condition.get("type", "price_above")
        cond_value = condition.get("value")
        cond_extra = json.dumps(condition.get("extra", {}))
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO subscriptions (user_id, symbol, condition_type, condition_value, condition_extra, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, sym, cond_type, cond_value, cond_extra, now),
            )
            conn.commit()
            return cursor.lastrowid

    def remove_subscription(self, subscription_id: int) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
            conn.commit()
            return cursor.rowcount > 0

    def deactivate_subscription(self, subscription_id: int) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "UPDATE subscriptions SET active = 0 WHERE id = ?",
                (subscription_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_subscriptions(self, user_id: Optional[str] = None, symbol: Optional[str] = None) -> list[dict]:
        query = "SELECT id, user_id, symbol, condition_type, condition_value, created_at, active FROM subscriptions WHERE 1=1"
        params = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.upper().strip())
        query += " ORDER BY created_at DESC"
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "symbol": r[2],
                "condition_type": r[3],
                "condition_value": r[4],
                "created_at": r[5],
                "active": bool(r[6]),
            }
            for r in rows
        ]

    def check_subscriptions(
        self,
        symbol: str,
        current_price: Optional[float] = None,
        current_rsi: Optional[float] = None,
        current_volume_ratio: Optional[float] = None,
        current_signal_score: Optional[float] = None,
    ) -> list[dict]:
        """
        Mevcut degerlere gore tetiklenen abonelikleri dondur.

        Donus: [{"subscription_id": int, "user_id": str, "message": str}]
        """
        sym = symbol.upper().strip()
        triggered = []
        subs = self.list_subscriptions(symbol=sym)

        for sub in subs:
            if not sub["active"]:
                continue
            cond_type = sub["condition_type"]
            cond_value = sub["condition_value"]
            msg = None

            if cond_type == "price_above" and current_price is not None and current_price >= cond_value:
                msg = f"{sym} fiyati {current_price} TL, {cond_value} TL uzerine cikti."
            elif cond_type == "price_below" and current_price is not None and current_price <= cond_value:
                msg = f"{sym} fiyati {current_price} TL, {cond_value} TL altina dustu."
            elif cond_type == "rsi_above" and current_rsi is not None and current_rsi >= cond_value:
                msg = f"{sym} RSI {current_rsi:.1f}, {cond_value} uzerine cikti."
            elif cond_type == "volume_spike" and current_volume_ratio is not None and current_volume_ratio >= cond_value:
                msg = f"{sym} hacim {current_volume_ratio:.1f}x patlamasi tespit edildi."
            elif cond_type == "signal_score" and current_signal_score is not None and current_signal_score >= cond_value:
                msg = f"{sym} sinyal skoru {current_signal_score}, esik {cond_value} uzerine cikti."

            if msg:
                triggered.append({
                    "subscription_id": sub["id"],
                    "user_id": sub["user_id"],
                    "message": msg,
                    "condition_type": cond_type,
                })
                self._record_trigger(sub["id"], current_price or cond_value, msg)
                self._update_last_triggered(sub["id"])

        return triggered

    def _record_trigger(self, subscription_id: int, trigger_value: float, message: str):
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO subscription_logs (subscription_id, triggered_at, trigger_value, message) VALUES (?, ?, ?, ?)",
                (subscription_id, now, trigger_value, message),
            )
            conn.commit()

    def _update_last_triggered(self, subscription_id: int):
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE subscriptions SET last_triggered = ? WHERE id = ?",
                (now, subscription_id),
            )
            conn.commit()

    def get_logs(self, subscription_id: Optional[int] = None, limit: int = 50) -> list[dict]:
        query = "SELECT id, subscription_id, triggered_at, trigger_value, message FROM subscription_logs WHERE 1=1"
        params = []
        if subscription_id:
            query += " AND subscription_id = ?"
            params.append(subscription_id)
        query += " ORDER BY triggered_at DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "subscription_id": r[1],
                "triggered_at": r[2],
                "trigger_value": r[3],
                "message": r[4],
            }
            for r in rows
        ]


if __name__ == "__main__":
    sm = SubscriptionManager()
    sid = sm.add_subscription("YOUR_CHAT_ID_HERE", "THYAO", {"type": "price_above", "value": 105.0})
    print("Subscription ID:", sid)
    triggers = sm.check_subscriptions("THYAO", current_price=106.0)
    print("Triggers:", triggers)

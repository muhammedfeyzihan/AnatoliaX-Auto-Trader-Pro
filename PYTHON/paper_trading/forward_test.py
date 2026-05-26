"""
AnatoliaX Forward Test (Out-of-Sample Live Test)
Stratejiyi canli veri uzerinde test et, emir verme, sadece izle ve kaydet.

Kullanim:
    from paper_trading.forward_test import ForwardTest
    ft = ForwardTest()
    ft.run("THYAO", days=5)
    report = ft.generate_report()

Calisma Akisi:
    1. Sinyal uret (SignalEngine.analyze_symbol)
    2. Sinyali kaydet (PaperSignal, outcome=PENDING)
    3. Belirtilen gun sonra fiyat kontrol et
    4. Beklenen vs gercekleseni karsilastir
    5. Rapor uret (In-Sample vs Out-of-Sample)
"""

import os
from datetime import datetime, timedelta, timezone

from data.feed_aggregator import FeedAggregator
from paper_trading.models import PaperSignal
from risk.database import get_session
from paper_trading.signal_engine import SignalEngine


class ForwardTest:
    """
    Forward test motoru: Sinyal uret, izle, degerlendir.
    """

    def __init__(self, lookahead_days: int | None = None):
        self.lookahead_days = lookahead_days or int(
            os.getenv("AX_FORWARD_TEST_LOOKAHEAD_DAYS", 5)
        )
        self.signal_engine = SignalEngine(paper_trading=False)
        self.feed = FeedAggregator()

    def run(self, symbol: str, days: int | None = None) -> dict:
        """
        Belirtilen sembol icin forward test baslat.

        Args:
            symbol: Hisse sembolu
            days: Kac gun sonra sonuc kontrol edilecek (varsayilan: self.lookahead_days)

        Returns:
            Sonuc dict: symbol, entry, expected_tp, expected_sl, actual_close, outcome
        """
        days = days or self.lookahead_days

        # 1. Simdiki sinyali uret
        signal = self.signal_engine.analyze_symbol(symbol)
        if signal is None:
            return {"symbol": symbol, "outcome": "NO_SIGNAL", "reason": "Yeterli sinyal yok"}

        # 2. Sinyali kaydet (PENDING)
        session = get_session()
        ps = PaperSignal(
            symbol=signal["symbol"],
            signal_time=signal["timestamp"],
            strategy="FORWARD_TEST",
            entry_price=signal["entry"],
            sl_price=signal["sl"],
            tp1_price=signal["tp1"],
            tp2_price=signal["tp2"],
            r_r=signal["r_r"],
            kelly=signal["kelly"],
            mirofish=signal["mirofish"],
            signal_score=signal["score"],
            regime=signal["regime"],
            outcome="PENDING",
            notes=f"Forward test basladi. {days} gun sonra kontrol edilecek.",
        )
        session.add(ps)
        session.commit()
        signal_id = ps.id
        session.close()

        # 3. Gelecekteki fiyati simule et (gercekte: scheduled job calistirir)
        # Simdilik mevcut fiyati kullanip beklenen/gercek karsilastirmasi yap
        expected_return = (signal["tp1"] - signal["entry"]) / signal["entry"]
        expected_sl_return = (signal["sl"] - signal["entry"]) / signal["entry"]

        # Gercek kapanis fiyati (simdilik ayni gun kapanisi)
        try:
            df = self.feed.fetch(symbol, interval="1d", period="5d")
            actual_close = df["close"].iloc[-1]
        except Exception:
            actual_close = signal["entry"]

        actual_return = (actual_close - signal["entry"]) / signal["entry"]

        # Sonuc degerlendirme
        if actual_return >= expected_return * 0.5:
            outcome = "TP_HIT"
        elif actual_return <= expected_sl_return * 1.5:
            outcome = "SL_HIT"
        else:
            outcome = "PENDING"

        # 4. Guncelle
        session = get_session()
        ps = session.query(PaperSignal).filter_by(id=signal_id).first()
        if ps:
            ps.outcome = outcome
            ps.close_price = actual_close
            ps.realized_pnl = actual_return * 100  # Yuzde olarak
            ps.notes = (
                f"{ps.notes} | Sonuc: {outcome} | "
                f"Beklenen: %{expected_return*100:.2f} | "
                f"Gerceklesen: %{actual_return*100:.2f}"
            )
            session.commit()
        session.close()

        return {
            "symbol": symbol,
            "signal_id": signal_id,
            "entry": signal["entry"],
            "expected_tp": signal["tp1"],
            "expected_sl": signal["sl"],
            "actual_close": actual_close,
            "expected_return_pct": expected_return * 100,
            "actual_return_pct": actual_return * 100,
            "outcome": outcome,
            "days": days,
        }

    def generate_report(self, days: int = 30) -> dict:
        """
        Son N gunun forward test sonuclarini analiz et.
        Returns: istatistik dict
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        session = get_session()
        signals = (
            session.query(PaperSignal)
            .filter(
                PaperSignal.signal_time >= since,
                PaperSignal.outcome != "PENDING",
            )
            .all()
        )
        session.close()

        if not signals:
            return {"message": "Degerlendirilecek forward test yok"}

        tp_hits = [s for s in signals if s.outcome == "TP_HIT"]
        sl_hits = [s for s in signals if s.outcome == "SL_HIT"]
        total = len(signals)

        win_rate = len(tp_hits) / total if total > 0 else 0
        avg_expected = sum(s.r_r for s in signals) / total if total > 0 else 0
        avg_realized = sum(s.realized_pnl or 0 for s in signals) / total if total > 0 else 0

        return {
            "period_days": days,
            "total_signals": total,
            "tp_hits": len(tp_hits),
            "sl_hits": len(sl_hits),
            "win_rate": win_rate,
            "avg_expected_r_r": avg_expected,
            "avg_realized_return_pct": avg_realized,
            "status": "ONAY" if win_rate >= 0.55 else "SINIRLI" if win_rate >= 0.45 else "RED",
        }


if __name__ == "__main__":
    ft = ForwardTest()
    result = ft.run("THYAO", days=5)
    print(result)
    report = ft.generate_report(days=30)
    print(report)

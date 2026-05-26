"""
AnatoliaX Telegram Reporter
Python tabanli Telegram bot modulu. Gunluk raporlar + anlik alarm.

Kullanim:
    from telegram.reporter import TelegramReporter
    reporter = TelegramReporter()
    reporter.send_evening_report()
    reporter.send_alert("Max Drawdown %10 asildi!")

Rapor Tipleri:
    - Morning (08:30): Makro durum, dunku performans, bugun plani
    - Opening (09:30): Gap-up adaylari, momentum
    - Midday (14:00): Portfoy durumu, gunluk P&L
    - Evening (18:00): Kapanis degerlendirme, gece swing, yarin plani
    - Alert (anlik): Risk limiti, yeni sinyal, SL tetiklenme
"""

import os
import requests
from datetime import datetime, timedelta

from paper_trading.paper_broker import PaperBroker
from paper_trading.signal_engine import SignalEngine
from risk.database import get_session
from paper_trading.models import PaperPortfolio, PaperSignal
from data.feed_aggregator import FeedAggregator


class TelegramReporter:
    """
    Telegram Bot API uzerinden rapor ve alarm gonderimi.
    """

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.getenv("AX_TELEGRAM_TOKEN", "")
        self.chat_id = chat_id or os.getenv("AX_TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.broker = PaperBroker()
        self.feed = FeedAggregator()

    def _send_message(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            print("UYARI: Telegram token/chat_id eksik. Mesaj gonderilemedi.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram gonderim hatasi: {e}")
            return False

    def send_morning_report(self) -> bool:
        """08:30 Sabah raporu."""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Dunku portfoy
        session = get_session()
        yesterday_pf = session.query(PaperPortfolio).filter_by(date=yesterday).first()
        session.close()

        y_pnl = yesterday_pf.daily_pnl if yesterday_pf else 0.0
        y_icon = "✅" if y_pnl >= 0 else "❌"

        text = f"""
📊 *AnatoliaX Sabah Raporu* ({today})

Dunku Performans:
{y_icon} Gunluk P&L: *{y_pnl:+.2f} TL*

Makro Durum:
🌍 Rejim: BULL (tahmini)
💵 USD/TRY: TradingView'dan kontrol edin
📈 VIX: TradingView'dan kontrol edin

Gunluk Plan:
🔍 09:30: Acilis momentum taramasi
📊 10:00: Teknik analiz (B-Teknik)
📰 10:30: Haber/Hafiza analizi (C/G)
⚖️  11:00: Risk degerlendirme (D)
🗳️  11:30: Konsey toplantisi

Bugsun gap-up adaylari icin 17:30'a kadar hazirlik.
"""
        return self._send_message(text.strip())

    def send_opening_report(self, symbols: list[str] | None = None) -> bool:
        """09:30 Acilis raporu: Gap-up adaylari ve momentum."""
        symbols = symbols or ["THYAO", "GARAN", "ASELS", "BIMAS", "KCHOL"]
        lines = ["📈 *AnatoliaX Acilis Raporu*", ""]
        lines.append("Gap-Up Adaylari:")
        lines.append("| Hisse | Acilis | Degisim |")
        lines.append("|-------|--------|---------|")

        for sym in symbols:
            try:
                df = self.feed.fetch(sym, interval="1d", period="5d")
                if len(df) >= 2:
                    prev = df["close"].iloc[-2]
                    curr = df["close"].iloc[-1]
                    change = ((curr - prev) / prev) * 100
                    icon = "🚀" if change > 2 else "📈" if change > 0 else "📉"
                    lines.append(f"| {sym} | {curr:.2f} | {icon} {change:+.2f}% |")
            except Exception:
                lines.append(f"| {sym} | N/A | Veri yok |")

        return self._send_message("\n".join(lines))

    def send_midday_report(self) -> bool:
        """14:00 Ogle raporu: Portfoy durumu."""
        summary = self.broker.get_portfolio_summary()

        pos_list = self.broker.get_open_positions()
        pos_lines = []
        for p in pos_list:
            pos_lines.append(f"• {p.symbol}: {p.size} adet @ {p.entry_price:.2f}")

        pos_text = "\n".join(pos_lines) if pos_lines else "Acik pozisyon yok"

        alert_text = ""
        if summary["alerts"]:
            alert_text = "\n".join([f"⚠️ {a}" for a in summary["alerts"]])

        text = f"""
📊 *AnatoliaX Ogle Raporu*

Portfoy Ozeti:
💰 Nakit: {summary['cash']:.2f} TL
📈 Toplam Deger: {summary['total_value']:.2f} TL
📉 Gunluk P&L: *{summary['daily_pnl']:+.2f} TL*
📊 Kumulatif P&L: {summary['cumulative_pnl']:+.2f} TL
📉 Max Drawdown: %{summary['max_drawdown']:.2f}

Acik Pozisyonlar ({summary['open_positions']}):
{pos_text}

{alert_text}
"""
        return self._send_message(text.strip())

    def send_evening_report(self, swing_candidates: list[dict] | None = None) -> bool:
        """18:00 Kapanis raporu."""
        summary = self.broker.get_portfolio_summary()
        today = datetime.now().strftime("%Y-%m-%d")

        # Swing adaylari (varsa)
        swing_text = ""
        if swing_candidates:
            swing_lines = ["| Hisse | Gap-Up% | Guven |", "|-------|---------|-------|"]
            for c in swing_candidates:
                swing_lines.append(f"| {c['symbol']} | {c['gap_up']:.0f}% | {c['grade']} |")
            swing_text = "\n".join(swing_lines)
        else:
            swing_text = "Bugun swing adayi tespit edilmedi."

        text = f"""
📊 *AnatoliaX Kapanis Raporu* ({today})

Gun Sonu Degerlendirme:
📈 Toplam Deger: {summary['total_value']:.2f} TL
📉 Gunluk P&L: *{summary['daily_pnl']:+.2f} TL*
📊 Kumulatif P&L: {summary['cumulative_pnl']:+.2f} TL
📉 Max Drawdown: %{summary['max_drawdown']:.2f}

Gece Swing Adaylari:
{swing_text}

Yarin Icin:
🔍 08:30 Makro guncelleme
📊 09:30 Acilis taramasi
🗳️  11:30 Konsey toplantisi

Iyi aksamlar, efendim.
"""
        return self._send_message(text.strip())

    def send_alert(self, message: str, level: str = "warning") -> bool:
        """
        Anlik alarm gonder.
        level: info / warning / critical
        """
        icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        icon = icons.get(level, "⚠️")
        text = f"{icon} *AnatoliaX Alarm*\n\n{message}"
        return self._send_message(text)

    def send_signal_alert(self, signal: dict) -> bool:
        """Yeni sinyal alarmi."""
        text = f"""
🎯 *Yeni Sinyal Tespit Edildi*

Hisse: *{signal['symbol']}*
Skor: {signal['score']:.0f}/100
Entry: {signal['entry']:.2f} TL
SL: {signal['sl']:.2f} TL
TP1: {signal['tp1']:.2f} TL
TP2: {signal['tp2']:.2f} TL
R:R: 1:{signal['r_r']:.1f}
Kelly: {signal['kelly']:.3f}

Durum: {'Paper trade ACILDI ✅' if signal.get('executed') else 'Sinyal kaydedildi ⏳'}
"""
        return self._send_message(text.strip())


def send_report(report_type: str) -> bool:
    """Helper: rapor tipine gore TelegramReporter metodunu cagir."""
    reporter = TelegramReporter()
    if report_type == "morning":
        return reporter.send_morning_report()
    elif report_type == "opening":
        return reporter.send_opening_report()
    elif report_type == "midday":
        return reporter.send_midday_report()
    elif report_type == "evening":
        return reporter.send_evening_report()
    else:
        return False


if __name__ == "__main__":
    reporter = TelegramReporter()
    reporter.send_morning_report()
    reporter.send_midday_report()
    reporter.send_evening_report()

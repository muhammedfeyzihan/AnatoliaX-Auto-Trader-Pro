"""
Test: PYTHON.risk.portfolio_monitor
Portfoy monitoru dogrulama: trade kaydetme, pozisyon kapatma, ozet, alarm.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.database import init_db, get_session
from risk.portfolio_monitor import PortfolioMonitor
from risk.models import Trade, DailyStats

# Test veritabanini baslat
init_db()


class TestPortfolioMonitor:
    def setup_method(self):
        # Her test oncesi tablolari temizle
        session = get_session()
        session.query(Trade).delete()
        session.query(DailyStats).delete()
        session.commit()
        session.close()
    def test_record_trade(self):
        monitor = PortfolioMonitor()
        monitor.record_trade(
            symbol="THYAO",
            side="BUY",
            size=100,
            price=103.0,
            commission=10.3,
            bsmv=10.3,
            strategy="EMA_CROSS",
            agent="B",
        )
        positions = monitor.get_open_positions()
        assert any(p.symbol == "THYAO" for p in positions)
        thyao = next(p for p in positions if p.symbol == "THYAO")
        assert thyao.size == 100

    def test_close_trade(self):
        monitor = PortfolioMonitor()
        trade = monitor.record_trade(
            symbol="THYAO",
            side="BUY",
            size=100,
            price=103.0,
            commission=10.3,
            bsmv=10.3,
            strategy="EMA_CROSS",
            agent="B",
        )
        monitor.close_trade(trade_id=trade.id, exit_price=110.0)
        positions = monitor.get_open_positions()
        assert not any(p.symbol == "THYAO" for p in positions)

    def test_portfolio_summary(self):
        monitor = PortfolioMonitor()
        monitor.record_trade(
            symbol="THYAO",
            side="BUY",
            size=100,
            price=103.0,
            commission=10.3,
            bsmv=10.3,
            strategy="EMA_CROSS",
            agent="B",
        )
        summary = monitor.get_portfolio_summary()
        assert "open_positions" in summary
        assert summary["open_positions"] == 1
        assert "alerts" in summary

    def test_multiple_positions(self):
        monitor = PortfolioMonitor()
        for sym in ["THYAO", "GARAN", "ISCTR"]:
            monitor.record_trade(
                symbol=sym,
                side="BUY",
                size=50,
                price=100.0,
                commission=5.0,
                bsmv=5.0,
                strategy="MOMENTUM",
                agent="B",
            )
        positions = monitor.get_open_positions()
        assert len(positions) == 3

    def test_end_of_day(self):
        monitor = PortfolioMonitor()
        monitor.record_trade(
            symbol="THYAO",
            side="BUY",
            size=100,
            price=103.0,
            commission=10.3,
            bsmv=10.3,
            strategy="EMA_CROSS",
            agent="B",
        )
        eod = monitor.end_of_day(capital=100000)
        assert eod.date is not None
        assert eod.total_trades >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

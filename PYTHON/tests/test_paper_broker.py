"""
Test: PYTHON.paper_trading.paper_broker
Paper broker dogrulama: emir, pozisyon, P&L, limit.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from risk.database import init_db, get_session
from paper_trading.paper_broker import PaperBroker
from paper_trading.models import PaperTrade, PaperPortfolio

# Test veritabanini baslat
init_db()


class TestPaperBroker:
    def setup_method(self):
        # Her test oncesi paper trading tablolarini temizle
        session = get_session()
        session.query(PaperTrade).delete()
        session.query(PaperPortfolio).delete()
        session.commit()
        session.close()
    def test_place_order(self):
        broker = PaperBroker(initial_capital=100000)
        trade = broker.place_order("THYAO", "BUY", 100, 103.0, sl=99.0, tp1=110.0)
        assert trade is not None
        assert trade.symbol == "THYAO"
        assert trade.status == "OPEN"

    def test_max_positions_limit(self):
        broker = PaperBroker(initial_capital=100000, max_positions=2)
        broker.place_order("THYAO", "BUY", 100, 103.0)
        broker.place_order("GARAN", "BUY", 100, 50.0)
        trade3 = broker.place_order("ASELS", "BUY", 100, 75.0)
        assert trade3 is None  # Limit asimi

    def test_close_trade(self):
        broker = PaperBroker(initial_capital=100000)
        trade = broker.place_order("THYAO", "BUY", 100, 103.0)
        assert trade is not None
        closed = broker.close_trade(trade.id, 110.0, reason="TP1")
        assert closed is not None
        assert closed.status == "CLOSED"
        assert closed.net_pnl is not None

    def test_close_trade_commission_included(self):
        broker = PaperBroker(initial_capital=100000)
        trade = broker.place_order("THYAO", "BUY", 100, 100.0)
        closed = broker.close_trade(trade.id, 105.0, reason="TP1")
        # Brut kar ~500, net kar komisyon dustu
        assert closed.net_pnl < 500.0
        assert closed.net_pnl > 0

    def test_get_open_positions(self):
        broker = PaperBroker(initial_capital=100000)
        broker.place_order("THYAO", "BUY", 100, 103.0)
        broker.place_order("GARAN", "BUY", 50, 50.0)
        pos = broker.get_open_positions()
        assert len(pos) == 2

    def test_portfolio_summary(self):
        broker = PaperBroker(initial_capital=100000)
        broker.place_order("THYAO", "BUY", 100, 103.0)
        summary = broker.get_portfolio_summary()
        assert "open_positions" in summary
        assert summary["open_positions"] == 1
        assert "alerts" in summary

    def test_daily_pnl(self):
        broker = PaperBroker(initial_capital=100000)
        trade = broker.place_order("THYAO", "BUY", 100, 100.0)
        broker.close_trade(trade.id, 105.0)
        pnl = broker.get_daily_pnl()
        assert pnl > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

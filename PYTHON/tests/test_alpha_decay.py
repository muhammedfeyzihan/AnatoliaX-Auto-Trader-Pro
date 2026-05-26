import pytest
from agents.alpha_decay import AlphaDecayDetector


def test_sharpe_20d_insufficient_data():
    det = AlphaDecayDetector()
    assert det.sharpe_20d() == 0.0


def test_sharpe_20d_with_data():
    det = AlphaDecayDetector()
    for i in range(25):
        det.ingest_trade(pnl=0.01 if i % 2 == 0 else -0.005)
    sharpe = det.sharpe_20d()
    assert isinstance(sharpe, float)


def test_win_rate_trend():
    det = AlphaDecayDetector()
    for i in range(30):
        det.ingest_trade(pnl=0.01)
    assert det.win_rate_trend(window=20) == 100.0


def test_profit_factor():
    det = AlphaDecayDetector()
    for i in range(10):
        det.ingest_trade(pnl=0.01 if i % 2 == 0 else -0.005)
    pf = det.profit_factor()
    assert pf > 0


def test_check_decay_triggers_kill_switch():
    det = AlphaDecayDetector()
    for i in range(25):
        det.ingest_trade(pnl=-0.05)
    result = det.check_decay()
    assert result["disabled"] is True
    assert result["kill_switch"] is True


def test_can_resume_after_cooldown():
    det = AlphaDecayDetector()
    det._kill_switch_triggered = True
    det._kill_switch_time = det._kill_switch_time = __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(hours=25)
    assert det.can_resume() is True


def test_cannot_resume_immediately():
    det = AlphaDecayDetector()
    det._kill_switch_triggered = True
    det._kill_switch_time = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    assert det.can_resume() is False

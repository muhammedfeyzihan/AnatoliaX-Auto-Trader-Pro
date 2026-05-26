"""
Test: PYTHON.telegram.subscription_manager
Abonelik ekleme, tetikleme, silme.
"""
import pytest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telegram.subscription_manager import SubscriptionManager


def _make_td():
    return Path(tempfile.mkdtemp())


class TestSubscriptionManager:
    def test_add_and_list(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sid = sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            subs = sm.list_subscriptions()
            assert len(subs) == 1
            assert subs[0]["symbol"] == "THYAO"
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_check_triggered(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            triggers = sm.check_subscriptions("THYAO", current_price=106.0)
            assert len(triggers) == 1
            assert "u1" == triggers[0]["user_id"]
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_check_not_triggered(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            triggers = sm.check_subscriptions("THYAO", current_price=104.0)
            assert len(triggers) == 0
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_price_below(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "price_below", "value": 100.0})
            triggers = sm.check_subscriptions("THYAO", current_price=99.0)
            assert len(triggers) == 1
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_rsi_above(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "rsi_above", "value": 70.0})
            triggers = sm.check_subscriptions("THYAO", current_rsi=75.0)
            assert len(triggers) == 1
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_volume_spike(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "volume_spike", "value": 3.0})
            triggers = sm.check_subscriptions("THYAO", current_volume_ratio=4.0)
            assert len(triggers) == 1
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_signal_score(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "signal_score", "value": 80.0})
            triggers = sm.check_subscriptions("THYAO", current_signal_score=85.0)
            assert len(triggers) == 1
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_remove_subscription(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sid = sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            assert sm.remove_subscription(sid) is True
            assert sm.list_subscriptions() == []
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_deactivate(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sid = sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            assert sm.deactivate_subscription(sid) is True
            triggers = sm.check_subscriptions("THYAO", current_price=106.0)
            assert len(triggers) == 0
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_logs(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sid = sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            sm.check_subscriptions("THYAO", current_price=106.0)
            logs = sm.get_logs(subscription_id=sid)
            assert len(logs) == 1
            assert "THYAO" in logs[0]["message"]
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_list_by_user(self):
        td = _make_td()
        try:
            sm = SubscriptionManager(db_path=td / "subs.db")
            sm.add_subscription("u1", "THYAO", {"type": "price_above", "value": 105.0})
            sm.add_subscription("u2", "GARAN", {"type": "price_above", "value": 50.0})
            subs = sm.list_subscriptions(user_id="u1")
            assert len(subs) == 1
            assert subs[0]["symbol"] == "THYAO"
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

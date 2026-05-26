"""
tests/test_kill_switch.py — KillSwitch birim testleri
"""
import pytest
from hft_pro.risk.kill_switch import KillSwitch


class TestKillSwitch:
    def test_arm_then_alive(self):
        ks = KillSwitch()
        ks.arm()
        assert ks.is_alive() is True

    def test_trigger_then_dead(self):
        ks = KillSwitch()
        ks.trigger("test reason")
        assert ks.is_alive() is False

    def test_log_entry_after_trigger(self):
        ks = KillSwitch()
        ks.trigger("manual")
        assert any("manual" in entry for entry in ks._log)

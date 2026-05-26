"""
tests/test_broker_risk.py — Broker risk testleri
"""
import unittest
from decimal import Decimal
from PYTHON.broker.risk.broker_risk import BrokerRiskManager
from PYTHON.broker.risk.settlement_risk import SettlementRisk
from PYTHON.broker.risk.credit_risk import CreditRisk


class TestBrokerRisk(unittest.TestCase):
    def test_pre_trade(self):
        rm = BrokerRiskManager()
        ok, reason = rm.pre_trade_check(Decimal("100000"), Decimal("50000"))
        self.assertTrue(ok)

    def test_settlement(self):
        sr = SettlementRisk()
        sr.add_settlement_obligation("BUY", "THYAO", Decimal("100"), Decimal("5000"))
        res = sr.check(Decimal("10000"), {})
        self.assertTrue(res["cash_ok"])

    def test_credit_margin_call(self):
        cr = CreditRisk()
        self.assertTrue(cr.margin_call(Decimal("1000"), Decimal("2000")))
        self.assertFalse(cr.margin_call(Decimal("3000"), Decimal("2000")))


if __name__ == "__main__":
    unittest.main()

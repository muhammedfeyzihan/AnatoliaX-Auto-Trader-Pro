"""
tests/test_reconciliation.py — Uzlastirma motoru birim testleri
"""
import pytest
from decimal import Decimal

from broker.reconciliation.position_recon import ReconciliationEngine


class TestReconciliationEngine:
    def test_reconcile_no_diff(self):
        engine = ReconciliationEngine()
        engine.set_internal({"THYAO": Decimal("100")})
        diffs = engine.reconcile({"THYAO": Decimal("100")})
        assert len(diffs) == 0

    def test_reconcile_diff(self):
        engine = ReconciliationEngine()
        engine.set_internal({"THYAO": Decimal("100")})
        diffs = engine.reconcile({"THYAO": Decimal("90")})
        assert len(diffs) == 1
        assert diffs[0].diff == Decimal("-10")

    def test_requires_human_review(self):
        engine = ReconciliationEngine()
        for _ in range(3):
            engine.set_internal({"THYAO": Decimal("100")})
            engine.reconcile({"THYAO": Decimal("90")})
        assert engine.requires_human_review(consecutive_days=3) is True

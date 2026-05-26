import pytest
import os
from compliance.regulatory_engine import ComplianceRegulatoryEngine


@pytest.fixture
def engine(tmp_path):
    db = str(tmp_path / "compliance_audit.db")
    return ComplianceRegulatoryEngine(db_path=db)


def test_log_order_event(engine):
    import time
    engine.log_order_event("ORD-1", "NEW", {"price": 100.0, "size": 10})
    state = engine.reconstruct_state(target_ts_ns=time.time_ns() + 10**18)
    assert len(state) >= 1
    assert state[0]["event"] == "NEW"


def test_reconstruct_state_empty(engine):
    state = engine.reconstruct_state(target_ts_ns=0)
    assert state == []


def test_detect_spoofing(engine):
    orders = [
        {"order_id": "A", "cancelled": True, "size": 3000, "lifetime_sec": 1.5},
        {"order_id": "B", "cancelled": False, "size": 100, "lifetime_sec": 10.0},
    ]
    alerts = engine.detect_spoofing(orders, avg_size=500, tau_sec=2.0)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "SPOOFING"


def test_detect_layering(engine):
    orders = []
    for i in range(6):
        orders.append({"order_id": f"O{i}", "price": 100.0, "executed": False})
    alerts = engine.detect_layering(orders, threshold=5)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "LAYERING"


def test_detect_wash_trading(engine):
    orders = [
        {"order_id": "B1", "side": "buy", "matched_with": "S1", "account": "ACC1", "matched_account": "ACC1"},
        {"order_id": "S1", "side": "sell", "matched_with": "B1", "account": "ACC1", "matched_account": "ACC1"},
    ]
    alerts = engine.detect_wash_trading(orders)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "WASH_TRADING"


def test_generate_sar(engine):
    sar = engine.generate_sar("rapid_withdrawal", [{"amount": 1000}])
    assert "sar_id" in sar
    assert sar["pattern"] == "rapid_withdrawal"
    assert sar["status"] == "filed"

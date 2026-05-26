import pytest
import os
from infrastructure.mlops_governance import MLOpsGovernance, ModelVersion


@pytest.fixture
def gov(tmp_path):
    db = str(tmp_path / "mlops_registry.db")
    return MLOpsGovernance(db_path=db)


def test_register_and_approve(gov):
    mv = ModelVersion(
        model_id="model-1",
        version="v1.0.0",
        sharpe=1.5,
        paper_trades=200,
        shadow_divergence=0.02,
        approved=True,
    )
    gov.register(mv)
    status = gov.approval_status("v1.0.0")
    assert status["approved"] is True
    assert status["gates"]["G1_backtest_sharpe"] is True
    assert status["gates"]["G2_paper_trades"] is True
    assert status["gates"]["G3_shadow_divergence"] is True
    assert status["gates"]["G4_human_approval"] is True


def test_approval_status_missing(gov):
    status = gov.approval_status("v999")
    assert status["approved"] is False


def test_rollback(gov):
    mv1 = ModelVersion(
        model_id="model-1",
        version="v1.0.0",
        sharpe=1.5,
        paper_trades=200,
        shadow_divergence=0.02,
        approved=True,
    )
    mv2 = ModelVersion(
        model_id="model-1",
        version="v1.1.0",
        sharpe=1.2,
        paper_trades=150,
        shadow_divergence=0.03,
        approved=True,
    )
    gov.register(mv1)
    gov.register(mv2)
    rollback_version = gov.rollback("model-1")
    assert rollback_version == "v1.0.0"


def test_drift_check(gov):
    result = gov.drift_check([0.1, 0.2, 0.3], [0.1, 0.2, 0.3])
    assert result["drift_detected"] is False


def test_drift_check_detected(gov):
    result = gov.drift_check([1.0, 1.1, 1.2], [0.1, 0.2, 0.3])
    assert result["drift_detected"] is True
    assert result["psi"] > 0.2

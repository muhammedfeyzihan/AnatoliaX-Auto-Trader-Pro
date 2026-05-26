import pytest
import os
from agents.macro_ontology import MacroOntologyEngine, CausalEdge


@pytest.fixture
def engine(tmp_path):
    db = str(tmp_path / "macro_ontology.db")
    return MacroOntologyEngine(db_path=db)


def test_add_edge(engine):
    engine.add_edge("Fed", "USDTRY", weight=0.8, time_lag_days=1.0)
    assert "Fed" in engine._vertices
    assert "USDTRY" in engine._vertices


def test_infer_impact_direct(engine):
    engine.add_edge("Fed", "USDTRY", weight=0.8, time_lag_days=1.0)
    impact = engine.infer_impact("Fed", "USDTRY", max_hops=3)
    assert impact == pytest.approx(0.8, rel=1e-2)


def test_infer_impact_indirect(engine):
    engine.add_edge("Fed", "DXY", weight=0.7, time_lag_days=1.0)
    engine.add_edge("DXY", "USDTRY", weight=0.6, time_lag_days=0.5)
    impact = engine.infer_impact("Fed", "USDTRY", max_hops=3)
    assert impact > 0.0
    assert impact <= 1.0


def test_infer_impact_no_path(engine):
    impact = engine.infer_impact("OPEC", "BIST", max_hops=3)
    assert impact == 0.0


def test_get_causal_paths(engine):
    engine.add_edge("Fed", "DXY", weight=0.7, time_lag_days=1.0)
    engine.add_edge("DXY", "USDTRY", weight=0.6, time_lag_days=0.5)
    paths = engine.get_causal_paths("Fed", "USDTRY", max_hops=3)
    assert len(paths) >= 1
    assert paths[0][0] == "Fed"
    assert paths[0][-1] == "USDTRY"

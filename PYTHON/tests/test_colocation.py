import pytest
from infrastructure.colocation import ColocationIntelligence


def test_measure_rtt_updates_baseline():
    col = ColocationIntelligence()
    col.measure_rtt("BIST", "IST", 12.0)
    assert col._rtt_matrix["BIST"]["IST"] == 12.0
    assert col._baselines["BIST"] == 12.0


def test_best_region():
    col = ColocationIntelligence()
    col.measure_rtt("BIST", "IST", 12.0)
    col.measure_rtt("BIST", "LON", 45.0)
    assert col.best_region("BIST") == "IST"


def test_best_region_unknown():
    col = ColocationIntelligence()
    assert col.best_region("NYSE") == "unknown"


def test_route_investigation_triggered():
    col = ColocationIntelligence()
    col.measure_rtt("BIST", "IST", 12.0)
    alert = col.route_investigation("BIST", current_rtt=25.0)
    assert alert is not None
    assert alert["alert"] is True


def test_route_investigation_clear():
    col = ColocationIntelligence()
    col.measure_rtt("BIST", "IST", 12.0)
    alert = col.route_investigation("BIST", current_rtt=13.0)
    assert alert is None


def test_get_heatmap():
    col = ColocationIntelligence()
    col.measure_rtt("BIST", "IST", 12.0)
    heatmap = col.get_heatmap()
    assert "BIST" in heatmap
    assert heatmap["BIST"]["IST"] == 12.0

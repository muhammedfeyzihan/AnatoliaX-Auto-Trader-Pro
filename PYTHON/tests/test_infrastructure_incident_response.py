import pytest
from infrastructure.incident_response import AutonomousIncidentResponse


def test_rule_registration_and_evaluation():
    resp = AutonomousIncidentResponse()
    triggered = []
    resp.register_rule("test_rule", lambda: True, lambda: triggered.append(True))
    resp.evaluate()
    assert len(triggered) == 1


def test_post_mortem():
    resp = AutonomousIncidentResponse()
    resp.register_rule("test_rule", lambda: True, lambda: None)
    resp.evaluate()
    incidents = resp._incidents
    assert len(incidents) >= 1
    pm = resp.generate_post_mortem(incidents[0].incident_id)
    assert pm is not None
    assert "root_cause" in pm

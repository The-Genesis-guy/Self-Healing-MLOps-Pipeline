#tests the decision logic

import pytest
from core.healer import Healer
from core.drift import DriftReport

def make_report(psi: float) -> DriftReport:
    """Helper: creates a DriftReport with a given PSI score.
    baseline_dist and current_dist are empty — healer only reads psi_score and drifted."""
    return DriftReport(feature="test_feature", psi_score=psi, drifted=psi >= 0.20,
                       baseline_dist={}, current_dist={})

def test_no_drift_no_action():
    healer = Healer()
    reports = {"amount": make_report(0.05)}
    decision = healer.decide(reports, current_f1=0.80)
    assert decision.action == "none"

def test_mild_drift_triggers_alert():
    healer = Healer()
    reports = {"amount": make_report(0.15)}   # above alert (0.10), below retrain (0.20)
    decision = healer.decide(reports, current_f1=0.80)
    assert decision.action == "alert"

def test_severe_drift_triggers_retrain():
    healer = Healer()
    reports = {"amount": make_report(0.50)}   # above retrain threshold
    decision = healer.decide(reports, current_f1=0.80)
    assert decision.action == "retrain"

def test_low_f1_triggers_rollback():
    healer = Healer()
    reports = {"amount": make_report(0.50)}   # would normally retrain
    decision = healer.decide(reports, current_f1=0.20)   # but F1 is below threshold
    assert decision.action == "rollback"   # rollback takes priority

def test_rollback_prioritised_over_retrain():
    """Even with severe drift, low F1 should trigger rollback not retrain."""
    healer = Healer()
    reports = {"amount": make_report(1.0), "foreign": make_report(0.8)}
    decision = healer.decide(reports, current_f1=0.10)
    assert decision.action == "rollback"

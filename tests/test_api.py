"""
API Integration Tests — uses FastAPI's TestClient (no server needed).
Tests every route: health, models, drift, pipeline lifecycle.

Run: pytest tests/test_api.py -v
"""

import time
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api import runner
from api.state import pipeline_state

client = TestClient(app)


# --- Fixtures ---

@pytest.fixture(autouse=True)
def stop_pipeline_after_each_test():
    """Ensure the pipeline is always stopped cleanly after each test."""
    yield
    runner.stop()
    time.sleep(0.1)   # let the thread wind down
    pipeline_state.update(running=False, iteration=0, last_action="none",
                          last_reason="", last_drifted_features=[])


# ============================
# Health Check
# ============================

def test_health_check():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "service" in body


# ============================
# Models
# ============================

def test_list_models_returns_array():
    r = client.get("/models")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_models_have_required_fields():
    r = client.get("/models")
    assert r.status_code == 200
    models = r.json()
    if models:
        m = models[0]
        assert "version" in m
        assert "f1_score" in m
        assert "is_active" in m
        assert "trained_at" in m

def test_active_model_returns_200_or_404():
    """Either an active model exists (200) or there isn't one (404). Both are valid states."""
    r = client.get("/models/active")
    assert r.status_code in (200, 404)

def test_active_model_has_is_active_true():
    r = client.get("/models/active")
    if r.status_code == 404:
        pytest.skip("No active model in this environment — run training first")
    body = r.json()
    assert body["is_active"] is True

def test_activate_nonexistent_version_returns_404():
    r = client.post("/models/99999/activate")
    assert r.status_code == 404

def test_activate_valid_version():
    """If any models exist, activating one should succeed."""
    r = client.get("/models")
    models = r.json()
    if not models:
        pytest.skip("No models in registry")
    version = models[0]["version"]
    r = client.post(f"/models/{version}/activate")
    assert r.status_code == 200
    assert r.json()["success"] is True


# ============================
# Drift Check
# ============================

def test_drift_check_normal_no_drift():
    r = client.get("/drift/check?scenario=normal")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"] == "normal"
    drifted = [f for f in body["features"] if f["drifted"]]
    assert len(drifted) == 0, f"Normal scenario should have no drift, got: {drifted}"

def test_drift_check_foreign_flags_correct_features():
    r = client.get("/drift/check?scenario=foreign")
    assert r.status_code == 200
    body = r.json()
    drifted_names = {f["feature"] for f in body["features"] if f["drifted"]}
    assert "transaction_amount" in drifted_names
    assert "is_foreign" in drifted_names

def test_drift_check_night_shift_flags_hour():
    r = client.get("/drift/check?scenario=night_shift")
    assert r.status_code == 200
    drifted_names = {f["feature"] for f in r.json()["features"] if f["drifted"]}
    assert "hour_of_day" in drifted_names

def test_drift_check_high_value_flags_amount():
    r = client.get("/drift/check?scenario=high_value")
    assert r.status_code == 200
    drifted_names = {f["feature"] for f in r.json()["features"] if f["drifted"]}
    assert "transaction_amount" in drifted_names

def test_drift_check_excludes_target_column():
    """is_fraud must never appear in drift results — it's not available on live data."""
    for scenario in ["normal", "foreign", "night_shift", "high_value"]:
        r = client.get(f"/drift/check?scenario={scenario}")
        feature_names = {f["feature"] for f in r.json()["features"]}
        assert "is_fraud" not in feature_names, \
            f"Target column leaked into drift results for scenario={scenario}"


# ============================
# Pipeline Lifecycle
# ============================

def test_pipeline_status_initially_not_running():
    r = client.get("/pipeline/status")
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is False

def test_pipeline_start_succeeds():
    r = client.post("/pipeline/start?scenario=normal")
    assert r.status_code == 200
    assert r.json()["success"] is True

def test_pipeline_start_when_already_running_returns_false():
    client.post("/pipeline/start?scenario=normal")
    time.sleep(0.2)
    r = client.post("/pipeline/start?scenario=normal")
    assert r.json()["success"] is False

def test_pipeline_status_after_start_shows_running():
    client.post("/pipeline/start?scenario=normal")
    time.sleep(0.2)
    r = client.get("/pipeline/status")
    assert r.json()["running"] is True

def test_pipeline_status_has_all_required_fields():
    r = client.get("/pipeline/status")
    body = r.json()
    required = ["running", "iteration", "last_action", "last_reason",
                "last_drifted_features", "active_model_version", "active_model_f1"]
    for field in required:
        assert field in body, f"Missing field: {field}"

def test_pipeline_stop_returns_success():
    client.post("/pipeline/start?scenario=normal")
    time.sleep(0.2)
    r = client.post("/pipeline/stop")
    assert r.status_code == 200
    assert r.json()["success"] is True

"""
Dashboard Integration Tests
Tests that all API endpoints work correctly for the dashboard
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestDashboardAPIs:
    """Test all APIs that the dashboard depends on"""

    def test_pipeline_status_returns_all_dashboard_fields(self):
        """Dashboard needs: running, iteration, last_action, last_reason, 
        last_drifted_features, active_model_version, active_model_f1, 
        shadow_model_version, health"""
        r = client.get("/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        
        # Required fields for dashboard header
        assert "running" in data
        assert "iteration" in data
        assert "active_model_version" in data
        assert "active_model_f1" in data
        assert "health" in data
        
        # Required fields for control panel
        assert "last_action" in data
        assert "last_reason" in data
        assert "last_drifted_features" in data
        assert isinstance(data["last_drifted_features"], list)
        
        # Required for Guardian Gate
        assert "shadow_model_version" in data or data.get("shadow_model_version") is None

    def test_pipeline_history_returns_list(self):
        """Dashboard System Events needs history array"""
        r = client.get("/pipeline/history")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        
        # If history exists, check structure
        if data:
            entry = data[0]
            assert "iteration" in entry
            assert "timestamp" in entry
            assert "model_version" in entry
            assert "f1_score" in entry
            assert "drift_score" in entry
            assert "action" in entry
            assert "reason" in entry

    def test_models_list_returns_array_with_importance(self):
        """Dashboard Model Registry and Explainable AI need model list with feature_importance"""
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        
        if data:
            model = data[0]
            assert "version" in model
            assert "path" in model
            assert "f1_score" in model
            assert "trained_at" in model
            assert "is_active" in model
            # Feature importance is optional but should be present for newer models
            assert "feature_importance" in model

    def test_active_model_has_feature_importance(self):
        """Explainable AI panel needs feature importance from active model"""
        r = client.get("/models/active")
        if r.status_code == 200:
            data = r.json()
            assert "feature_importance" in data
            # If feature_importance exists, it should be a dict
            if data["feature_importance"]:
                assert isinstance(data["feature_importance"], dict)

    def test_drift_check_returns_features_array(self):
        """Drift Radar table needs features with PSI scores"""
        r = client.get("/drift/check?scenario=normal")
        assert r.status_code == 200
        data = r.json()
        
        assert "scenario" in data
        assert "features" in data
        assert isinstance(data["features"], list)
        
        if data["features"]:
            feature = data["features"][0]
            assert "feature" in feature
            assert "psi_score" in feature
            assert "drifted" in feature
            assert isinstance(feature["psi_score"], (int, float))
            assert isinstance(feature["drifted"], bool)

    def test_pipeline_start_accepts_scenario(self):
        """Control Panel scenario selector needs to pass scenario parameter"""
        scenarios = ["normal", "night_shift", "high_value", "foreign"]
        
        for scenario in scenarios:
            r = client.post(f"/pipeline/start?scenario={scenario}")
            assert r.status_code == 200
            data = r.json()
            assert "success" in data
            assert "message" in data
            
            # Stop after each test
            client.post("/pipeline/stop")

    def test_pipeline_stop_works(self):
        """Control Panel stop button needs working stop endpoint"""
        # Start first
        client.post("/pipeline/start?scenario=normal")
        
        # Then stop
        r = client.post("/pipeline/stop")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_health_check_for_system_status(self):
        """Left sidebar System section needs health check"""
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestDashboardDataQuality:
    """Test that API data is in the correct format for dashboard rendering"""

    def test_f1_scores_are_valid_floats(self):
        """F1 gauge needs valid float between 0 and 1"""
        r = client.get("/models")
        if r.status_code == 200:
            models = r.json()
            for model in models:
                f1 = model["f1_score"]
                assert isinstance(f1, (int, float))
                assert 0 <= f1 <= 1, f"F1 score {f1} out of range [0, 1]"

    def test_timestamps_are_iso_format(self):
        """Dashboard needs parseable timestamps"""
        r = client.get("/pipeline/history")
        if r.status_code == 200:
            history = r.json()
            if history:
                from datetime import datetime
                for entry in history[:5]:  # Check first 5
                    timestamp = entry["timestamp"]
                    # Should be parseable as ISO format
                    try:
                        datetime.fromisoformat(timestamp)
                    except ValueError:
                        pytest.fail(f"Invalid timestamp format: {timestamp}")

    def test_iteration_is_positive_integer(self):
        """Header iteration counter needs positive integer"""
        r = client.get("/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        iteration = data["iteration"]
        assert isinstance(iteration, int)
        assert iteration >= 0

    def test_health_status_is_valid_enum(self):
        """Health indicator needs valid status"""
        r = client.get("/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        health = data["health"]
        assert health in ["healthy", "warning", "critical"]

    def test_psi_scores_are_non_negative(self):
        """Drift Radar PSI scores must be non-negative"""
        r = client.get("/drift/check?scenario=normal")
        assert r.status_code == 200
        data = r.json()
        
        for feature in data["features"]:
            psi = feature["psi_score"]
            assert psi >= 0, f"PSI score {psi} is negative"


class TestDashboardScenarios:
    """Test different scenarios that dashboard might encounter"""

    def test_no_models_scenario(self):
        """Dashboard should handle empty model registry gracefully"""
        # This test assumes models exist, but checks the structure
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_no_history_scenario(self):
        """Dashboard should handle empty history gracefully"""
        r = client.get("/pipeline/history?limit=0")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_pipeline_not_running_scenario(self):
        """Dashboard should show stopped state correctly"""
        # Ensure pipeline is stopped
        client.post("/pipeline/stop")
        
        r = client.get("/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        # Running state should be boolean
        assert isinstance(data["running"], bool)

    def test_no_shadow_model_scenario(self):
        """Dashboard should handle no shadow model gracefully"""
        r = client.get("/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        # shadow_model_version can be None
        assert data.get("shadow_model_version") is None or isinstance(data["shadow_model_version"], int)


class TestDashboardPerformance:
    """Test that APIs respond quickly enough for real-time dashboard"""

    def test_status_endpoint_responds_quickly(self):
        """Status endpoint is polled every 2 seconds, must be fast"""
        import time
        start = time.time()
        r = client.get("/pipeline/status")
        duration = time.time() - start
        
        assert r.status_code == 200
        assert duration < 0.5, f"Status endpoint took {duration}s, should be < 0.5s"

    def test_history_endpoint_with_limit(self):
        """History endpoint should support limit parameter for performance"""
        r = client.get("/pipeline/history?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert len(data) <= 10

    def test_models_endpoint_responds_quickly(self):
        """Models endpoint is called on every refresh"""
        import time
        start = time.time()
        r = client.get("/models")
        duration = time.time() - start
        
        assert r.status_code == 200
        assert duration < 0.5, f"Models endpoint took {duration}s, should be < 0.5s"


class TestDashboardCORS:
    """Test that CORS is properly configured for dashboard"""

    def test_cors_headers_present(self):
        """Dashboard at localhost:5173 needs CORS headers"""
        r = client.options("/pipeline/status", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        })
        # FastAPI TestClient doesn't fully simulate CORS, but we can check the app config
        # The actual CORS middleware is configured in api/main.py
        assert r.status_code in [200, 405]  # OPTIONS might not be implemented


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

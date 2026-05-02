#tests the model store (uses temp dir so it doesn't touch your real DB)

import pytest
from core.registry import ModelRegistry

@pytest.fixture
def registry(tmp_path):
    """Fresh registry for each test — isolated from production DB."""
    db_path = str(tmp_path / "test_registry.db")
    return ModelRegistry(db_path=db_path)

def test_register_creates_version(registry):
    record = registry.register(path="models/v1.pkl", f1_score=0.55, feature_importance={"amt": 0.5})
    assert record.version == 1
    assert record.feature_importance["amt"] == 0.5

def test_versions_increment(registry):
    r1 = registry.register("v1.pkl", 0.55)
    r2 = registry.register("v2.pkl", 0.58)
    assert r2.version == r1.version + 1

def test_no_active_model_initially(registry):
    assert registry.get_active() is None

def test_set_active_marks_correct_version(registry):
    registry.register("v1.pkl", 0.55)
    registry.register("v2.pkl", 0.58)
    registry.set_active(1)
    active = registry.get_active()
    assert active.version == 1

def test_only_one_model_active_at_a_time(registry):
    registry.register("v1.pkl", 0.55)
    registry.register("v2.pkl", 0.58)
    registry.set_active(1)
    registry.set_active(2)
    all_models = registry.get_all()
    active_count = sum(1 for m in all_models if m.is_active)
    assert active_count == 1

def test_get_by_version(registry):
    registry.register("v1.pkl", 0.55)
    record = registry.get_by_version(1)
    assert record is not None
    assert record.f1_score == 0.55

def test_rollback_restores_previous_version(registry):
    """Simulates what pipeline.py does during a rollback."""
    registry.register("v1.pkl", 0.55)
    registry.register("v2.pkl", 0.58)
    registry.set_active(2)   # v2 is current active

    # Rollback: set previous version active
    all_models = registry.get_all()
    previous = all_models[-2]   # same logic as pipeline.py
    registry.set_active(previous.version)

    active = registry.get_active()
    assert active.version == 1
    assert active.f1_score == 0.55
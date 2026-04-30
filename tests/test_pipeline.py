"""
Integration tests — wire Retrainer + Registry + Healer + calculate_drift together.
These tests verify the full cycle without mocking internals.
All model files are written to tmp_path so nothing touches the production models/ dir.
"""

import numpy as np
import pandas as pd
import pytest

from core.registry import ModelRegistry
from core.retrainer import Retrainer
from core.drift import calculate_drift
from core.healer import Healer

CATEGORICAL_COLS = ["category"]
TARGET_COL = "is_fraud"


def make_data(seed=42, n=300, fraud_rate=0.12):
    """Minimal dataset with a real signal — foreign/night = higher fraud."""
    rng = np.random.RandomState(seed)
    is_foreign = rng.choice([0, 1], n, p=[0.9, 0.1])
    hour = rng.randint(0, 24, n)
    amount = rng.exponential(200, n)
    category = rng.choice(["grocery", "online", "travel"], n)

    is_high_risk = (is_foreign == 1) | (hour < 5)
    fraud_prob = np.where(is_high_risk, 0.45, 0.02)
    is_fraud = (rng.random(n) < fraud_prob).astype(int)

    return pd.DataFrame({
        "amount": amount,
        "hour": hour,
        "is_foreign": is_foreign,
        "category": category,
        "is_fraud": is_fraud,
    })


@pytest.fixture
def registry(tmp_path):
    return ModelRegistry(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def retrainer(registry, tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return Retrainer(
        registry=registry,
        categorical_columns=CATEGORICAL_COLS,
        models_dir=str(models_dir)
    )


# --- Test 1: Full train → drift check → no action cycle ---

def test_train_then_no_drift_gives_no_action(registry, retrainer):
    """Train v1, check drift against identical data — healer should do nothing."""
    baseline = make_data(seed=0)
    result = retrainer.retrain(baseline, TARGET_COL)
    assert result.promoted
    assert registry.get_active().version == 1

    # Identical data — no drift
    reports = calculate_drift(
        baseline.drop(columns=[TARGET_COL]),
        baseline.drop(columns=[TARGET_COL]),
        categorical_columns=CATEGORICAL_COLS,
    )
    decision = Healer().decide(reports, current_f1=result.new_f1)
    assert decision.action == "none"


# --- Test 2: Each retrain gets a unique file, even when rejected ---

def test_each_retrain_gets_unique_filename(registry, retrainer, tmp_path):
    """
    Rejected models should not overwrite each other.
    v1 promoted, v2 and v3 saved to separate files even if rejected.
    """
    baseline = make_data(seed=0)

    # v1 — always promotes (no previous model)
    retrainer.retrain(baseline, TARGET_COL)

    # v2 and v3 — may or may not be promoted, but must have unique files
    retrainer.retrain(baseline, TARGET_COL)
    retrainer.retrain(baseline, TARGET_COL)

    model_files = list((tmp_path / "models").glob("*.pkl"))
    filenames = {f.name for f in model_files}

    # 3 retrains → 3 unique files
    assert len(filenames) == 3
    assert "v1.pkl" in filenames
    assert "v2.pkl" in filenames
    assert "v3.pkl" in filenames


# --- Test 3: Rollback restores the previous active model ---

def test_rollback_cycle(registry, retrainer):
    """Simulate the rollback path in pipeline.py — previous version restored."""
    baseline = make_data(seed=0)

    retrainer.retrain(baseline, TARGET_COL)   # v1, promoted
    retrainer.retrain(baseline, TARGET_COL)   # v2, promoted (same data, F1 >=)
    assert registry.get_active().version == 2

    # Rollback: same logic as pipeline.py ACT block
    all_models = registry.get_all()
    previous = all_models[-2]
    registry.set_active(previous.version)

    assert registry.get_active().version == 1


# --- Test 4: Registry grows correctly across promoted and rejected models ---

def test_registry_grows_with_every_retrain(registry, retrainer):
    """Every retrain registers a DB record — even rejected ones."""
    baseline = make_data(seed=0)

    retrainer.retrain(baseline, TARGET_COL)
    retrainer.retrain(baseline, TARGET_COL)
    retrainer.retrain(baseline, TARGET_COL)

    all_models = registry.get_all()
    assert len(all_models) == 3
    # Versions are sequential
    assert [m.version for m in all_models] == [1, 2, 3]

import os
import pandas as pd
import numpy as np
import pytest
import sys
import pathlib

# Ensure repo root is importable when running pytest
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pipeline import run_pipeline
from core.history import HistoryLogger
import config
from core.registry import ModelRegistry
from core.retrainer import Retrainer


class SimpleAdapter:
    """Lightweight adapter for testing the pipeline without large datasets."""
    def __init__(self, tmpdir):
        self.registry_path = os.path.join(str(tmpdir), "models", "registry.db")
        self.categorical_columns = []
        self.target_column = "label"
        self._iter = 0

    def load_baseline(self):
        # Create a simple balanced baseline
        n = 200
        rng = np.random.RandomState(42)
        X1 = rng.normal(loc=0.0, scale=1.0, size=(n, 2))
        y = rng.randint(0, 2, size=(n,))
        df = pd.DataFrame(X1, columns=["x1", "x2"])
        df[self.target_column] = y
        return df

    def get_current_data(self):
        # Return slightly different data each call to mimic streaming
        self._iter += 1
        n = 50
        rng = np.random.RandomState(100 + self._iter)
        # Introduce mild drift on second iteration
        shift = 0.0 if self._iter == 1 else 0.5
        X1 = rng.normal(loc=shift, scale=1.0, size=(n, 2))
        y = rng.randint(0, 2, size=(n,))
        df = pd.DataFrame(X1, columns=["x1", "x2"])
        df[self.target_column] = y
        return df


@pytest.mark.e2e
def test_pipeline_end_to_end(tmp_path, monkeypatch):
    # Run the pipeline in a temporary working directory so databases are isolated
    monkeypatch.chdir(tmp_path)

    # Speed up the loop for tests
    monkeypatch.setattr(config, 'LOOP_INTERVAL_SECONDS', 0)

    adapter = SimpleAdapter(tmp_path)

    # Ensure an initial active model exists (train baseline)
    registry = ModelRegistry(db_path=adapter.registry_path)
    retrainer = Retrainer(registry=registry, categorical_columns=adapter.categorical_columns, models_dir="models")
    baseline = adapter.load_baseline()
    retrainer.retrain(baseline, target_column=adapter.target_column)

    # Run a short pipeline
    run_pipeline(adapter=adapter, max_iterations=3)

    # Verify history DB has at least 3 entries
    history = HistoryLogger(db_path=os.path.join("models", "history.db"))
    entries = history.get_recent(limit=10)
    assert len(entries) >= 3
    # Ensure entries have the expected fields
    for e in entries[:3]:
        assert hasattr(e, 'iteration')
        assert hasattr(e, 'action')
        assert e.f1_score is not None

import pathlib
import sys
import time

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

# Ensure repo root is importable
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from api.main import app
from api import runner
from core.registry import ModelRegistry
from core.retrainer import Retrainer


class LifecycleAdapter:
    """Small adapter used to exercise the real pipeline start/stop flow."""

    def __init__(self, tmpdir):
        self.registry_path = str(pathlib.Path(tmpdir) / "models" / "registry.db")
        self.categorical_columns = []
        self.target_column = "label"
        self._current = 0

        registry = ModelRegistry(db_path=self.registry_path)
        if registry.get_active() is None:
            retrainer = Retrainer(registry=registry, categorical_columns=[])
            retrainer.retrain(self.load_baseline(), target_column=self.target_column)

    def load_baseline(self):
        rng = np.random.RandomState(7)
        X = rng.normal(0.0, 1.0, size=(120, 2))
        y = rng.randint(0, 2, size=120)
        df = pd.DataFrame(X, columns=["x1", "x2"])
        df[self.target_column] = y
        return df

    def get_current_data(self):
        self._current += 1
        rng = np.random.RandomState(50 + self._current)
        # Keep the data stable so the loop logs 'none' and remains healthy.
        X = rng.normal(0.0, 1.0, size=(40, 2))
        y = rng.randint(0, 2, size=40)
        df = pd.DataFrame(X, columns=["x1", "x2"])
        df[self.target_column] = y
        return df


def test_pipeline_start_and_stop(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "LOOP_INTERVAL_SECONDS", 0)

    adapter = LifecycleAdapter(tmp_path)
    monkeypatch.setattr("api.routes.pipeline.FraudAdapter", lambda scenario="normal": adapter)

    with TestClient(app) as client:
        start = client.post("/pipeline/start")
        assert start.status_code == 200
        assert start.json()["success"] is True

        # Wait briefly for the background thread to set its running flag.
        for _ in range(20):
            status = client.get("/pipeline/status")
            assert status.status_code == 200
            if status.json()["running"]:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("pipeline did not enter running state")

        stop = client.post("/pipeline/stop")
        assert stop.status_code == 200
        assert stop.json()["success"] is True

        for _ in range(20):
            status = client.get("/pipeline/status")
            assert status.status_code == 200
            if not status.json()["running"]:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("pipeline did not stop")

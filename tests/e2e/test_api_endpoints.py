import sys
import pathlib

# Ensure repo root is importable
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
from api.main import app


def test_pipeline_status_and_history():
    client = TestClient(app)

    r = client.get('/pipeline/status')
    assert r.status_code == 200
    body = r.json()
    assert 'running' in body

    r2 = client.get('/pipeline/history?limit=5')
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)

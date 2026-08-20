import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rooms import ROOMS


@pytest.fixture(autouse=True)
def isolated_rooms_and_logs(tmp_path, monkeypatch):
    """Fresh room registry per test; match logs go to a temp dir, never to
    the real output/ folder."""
    monkeypatch.setenv("CHESSSTRATEGO_OUTPUT_DIR", str(tmp_path))
    ROOMS.clear()
    yield
    ROOMS.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

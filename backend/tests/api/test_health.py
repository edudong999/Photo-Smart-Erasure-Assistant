import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("AI_CLIENT_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ai_reachable" in data
    assert "version" in data

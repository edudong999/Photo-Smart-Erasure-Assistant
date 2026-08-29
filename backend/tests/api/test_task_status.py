import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings


def _png_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _mask_bytes(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("L", size, 255).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("AI_CLIENT_MODE", "mock")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_get_task_returns_processing_or_success(client):
    submit = client.post(
        "/api/v1/inpaint",
        files={
            "image": ("i.png", _png_bytes(), "image/png"),
            "mask": ("m.png", _mask_bytes(), "image/png"),
        },
    )
    task_id = submit.json()["task_id"]

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ("processing", "success")
    if data["status"] == "success":
        assert data["result"]["result_url"].endswith(".png")


def test_get_nonexistent_task_returns_404(client):
    resp = client.get("/api/v1/tasks/t_doesnotexist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"
